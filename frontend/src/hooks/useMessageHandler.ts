import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import type { ChatResponse } from '../api'
import { ChatService } from '../api'
import { useAppContext } from '../context/AppContext'
import { handleUnauthorized } from '../utils/ApiClient'
import { tokenManager } from '../utils/TokenManager'

function getStreamBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
  return raw.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '')
}

interface UseMessageHandlerProps {
  sessionId: string | undefined
}

export interface SiblingInfo {
  total: number
  current: number // 1-based
}

export interface ToolCall {
  id?: string
  name?: string
  args?: Record<string, unknown>
  [key: string]: unknown
}

export interface PendingApproval {
  messageId: string
  toolCalls: ToolCall[]
}

interface UseMessageHandlerReturn {
  /** 当前激活路径上的消息（有序，直接用于渲染） */
  displayMessages: ChatResponse[]
  isLoading: boolean
  isCompressing: boolean
  editingMessageId: string | null
  editingContent: string
  pendingApproval: PendingApproval | null
  streamError: string | null
  setEditingContent: React.Dispatch<React.SetStateAction<string>>
  handleSendMessage: (
    message: string,
    fileIds?: number[],
    files?: ChatResponse['files']
  ) => Promise<void>
  handleApproveTools: (approved: boolean) => Promise<void>
  handleCompress: () => Promise<void>
  handleStartEdit: (messageId: string, currentContent: string) => void
  handleCancelEdit: () => void
  handleSaveEdit: (messageId: string) => Promise<void>
  handleRegenerate: (messageId: string) => Promise<void>
  handleSiblingSwitch: (messageId: string, direction: 'prev' | 'next') => void
  getSiblingInfo: (messageId: string) => SiblingInfo | undefined
  clearStreamError: () => void
  stopStream: () => void
}

// ─── 树工具函数 ────────────────────────────────────────────────────────────────

/** 扁平消息列表 → parentId → children[] 的 Map */
function buildChildrenMap(messages: ChatResponse[]): Map<string | null, ChatResponse[]> {
  const map = new Map<string | null, ChatResponse[]>()
  for (const msg of messages) {
    const key = msg.parent_id ?? null
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(msg)
  }
  return map
}

/**
 * 从指定 parentId 往下，每层取最后一个子节点（最新生成的），返回路径 id 数组。
 * startParentId = null 表示从根开始。
 */
function getDefaultSubPath(
  startParentId: string | null,
  childrenMap: Map<string | null, ChatResponse[]>
): string[] {
  const path: string[] = []
  let current: string | null = startParentId

  while (true) {
    const children = childrenMap.get(current)
    if (!children || children.length === 0) break
    const next = children[children.length - 1]
    path.push(next.id)
    current = next.id!
  }

  return path
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export const useMessageHandler = ({
  sessionId,
}: UseMessageHandlerProps): UseMessageHandlerReturn => {
  const { refreshSessions } = useAppContext()

  /** 所有消息的扁平列表（原始数据源，包含所有历史分支） */
  const [allMessages, setAllMessages] = useState<ChatResponse[]>([])
  /** 当前激活路径（有序 id 数组，代表从根到叶的一条链） */
  const [activePath, setActivePath] = useState<string[]>([])

  const [isLoading, setIsLoading] = useState(false)
  const [isCompressing, setIsCompressing] = useState(false)
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [editingContent, setEditingContent] = useState('')
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null)
  const [streamError, setStreamError] = useState<string | null>(null)

  // Ref for latest allMessages accessible inside async stream handlers
  const allMessagesRef = useRef<ChatResponse[]>([])
  useEffect(() => {
    allMessagesRef.current = allMessages
  }, [allMessages])

  // 用户主动打断当前流式回复（发送/重试/审批后恢复）
  const abortCtrlRef = useRef<AbortController | null>(null)
  const stopStream = useCallback(() => {
    abortCtrlRef.current?.abort()
    abortCtrlRef.current = null
    setIsLoading(false)
  }, [])

  // sessionId 切换时打断上一会话残留的流，避免旧 chunk 串到新会话 UI。
  // 注意：仅在 sessionId 实际变化时触发，组件 unmount（如切到别的页面）不 abort，
  // 后端依旧能跑完并落库。
  const prevSessionIdRef = useRef(sessionId)
  useEffect(() => {
    if (prevSessionIdRef.current !== sessionId) {
      abortCtrlRef.current?.abort()
      abortCtrlRef.current = null
      setIsLoading(false)
      setPendingApproval(null)
      setStreamError(null)
    }
    prevSessionIdRef.current = sessionId
  }, [sessionId])

  // ── 派生状态 ──────────────────────────────────────────────────────────────

  /** 当前展示的有序消息列表，直接用于渲染 */
  const displayMessages = useMemo(
    () =>
      activePath
        .map((id) => allMessages.find((m) => m.id === id))
        .filter((m): m is ChatResponse => !!m),
    [activePath, allMessages]
  )

  // ── 工具 ──────────────────────────────────────────────────────────────────

  function normalizeContent(content: unknown): string {
    if (content === null || content === undefined) return ''
    if (typeof content === 'string') return content
    try {
      return JSON.stringify(content, null, 2)
    } catch {
      return '[non-serializable]'
    }
  }

  /** 获取某条消息的兄弟导航信息（仅当兄弟数 > 1 时返回） */
  const getSiblingInfo = useCallback(
    (messageId: string): SiblingInfo | undefined => {
      const msg = allMessages.find((m) => m.id === messageId)
      if (!msg) return undefined

      const siblings = buildChildrenMap(allMessages).get(msg.parent_id ?? null) ?? []
      if (siblings.length <= 1) return undefined

      const idx = siblings.findIndex((m) => m.id === messageId)
      return { total: siblings.length, current: idx + 1 }
    },
    [allMessages]
  )

  // ── 流式处理 ──────────────────────────────────────────────────────────────

  function handleStreamChunk(
    chunkId: string,
    type: string,
    rawContent: unknown,
    toolCalls?: ToolCall[],
    parentId?: string | null,
    usageMetadata?: Record<string, unknown> | null
  ) {
    const content = normalizeContent(rawContent)

    setAllMessages((prev) => {
      const index = prev.findIndex((m) => m.id === chunkId)

      // 流式 AI chunk：追加内容到已有节点，或新建节点
      if (type === 'AIMessageChunk') {
        if (!content && !usageMetadata) return prev

        if (index !== -1) {
          const updated = [...prev]
          updated[index] = {
            ...updated[index],
            ...(content && { content: (updated[index].content as string) + content }),
            ...(usageMetadata && { usage_metadata: usageMetadata }),
          }
          return updated
        }

        if (!content) return prev

        return [
          ...prev,
          {
            id: chunkId,
            type: 'ai' as const,
            content,
            // parent 为全量列表最后一条（流式场景下即当前激活末尾的 human 消息）
            parent_id: parentId,
            tool_calls: toolCalls,
          },
        ]
      }

      // 完整 ai / tool / human 消息：直接覆盖或新建
      if (type === 'ai' || type === 'tool' || type === 'human') {
        if (index !== -1) {
          const updated = [...prev]
          updated[index] = {
            ...updated[index],
            content,
            // 用完整消息的 parent_id 修正流式 chunk 阶段可能写入的错误 parent_id
            ...(parentId !== undefined && { parent_id: parentId }),
            tool_calls: toolCalls ?? updated[index].tool_calls ?? [],
            ...(usageMetadata !== undefined && { usage_metadata: usageMetadata }),
          }
          return updated
        }

        return [
          ...prev,
          {
            id: chunkId,
            type: type,
            content,
            parent_id: parentId ?? prev[prev.length - 1]?.id ?? null,
            tool_calls: toolCalls,
            ...(usageMetadata !== undefined && { usage_metadata: usageMetadata }),
          },
        ]
      }

      return prev
    })

    // 将新节点追加到激活路径末尾（幂等）
    setActivePath((prev) => {
      if (prev[prev.length - 1] === chunkId) return prev
      return [...prev, chunkId]
    })
  }

  function handleStreamMessage(raw: string) {
    const parsed = JSON.parse(raw)
    if (!['AIMessageChunk', 'ai', 'tool', 'human'].includes(parsed.type)) return
    const chunk = parsed.data
    handleStreamChunk(
      chunk.id,
      parsed.type,
      chunk.content,
      chunk.tool_calls,
      chunk.parent_id,
      chunk.usage_metadata
    )
  }

  async function readSseStream(
    body: ReadableStream<Uint8Array>,
    onEvent: (eventType: string, dataLine: string) => boolean
  ): Promise<void> {
    const reader = body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    outer: while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() || ''
      for (const block of blocks) {
        if (!block.trim()) continue
        let eventType = 'message'
        let dataLine = ''
        for (const line of block.split('\n')) {
          if (line.startsWith('event:')) eventType = line.slice(6).trim()
          else if (line.startsWith('data:')) dataLine = line.slice(5).trim()
        }
        if (!dataLine) continue
        if (onEvent(eventType, dataLine)) break outer
      }
    }
  }

  async function processStream(response: Response) {
    if (!response.body) return
    await readSseStream(response.body, (eventType, dataLine) => {
      if (eventType === 'done') return true
      if (eventType === 'error') {
        const data = JSON.parse(dataLine) as { message?: string }
        setStreamError(data.message ?? '发生未知错误')
        return true
      }
      if (eventType === 'tool_approval_required') {
        const data = JSON.parse(dataLine) as { message_id: string }
        const aiMsg = allMessagesRef.current.find((m) => m.id === data.message_id)
        setPendingApproval({
          messageId: data.message_id,
          toolCalls: aiMsg?.tool_calls ?? [],
        })
        setIsLoading(false)
        return true
      }
      if (eventType === 'session_title') {
        refreshSessions()
        return false
      }
      handleStreamMessage(dataLine)
      return false
    })
  }

  async function startChatStream(
    sid: string,
    body: { content: string | null; parent_id: string | null; id: string; file_ids?: number[] }
  ) {
    const baseUrl = getStreamBaseUrl()
    const token = tokenManager.getToken() ?? ''

    const controller = new AbortController()
    abortCtrlRef.current = controller

    try {
      const res = await fetch(`${baseUrl}/api/v1/chat/${sid}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (res.status === 401) {
        handleUnauthorized()
        return
      }

      await processStream(res)
    } catch (error) {
      if ((error as Error)?.name !== 'AbortError') {
        console.error('Stream error:', error)
      }
    } finally {
      if (abortCtrlRef.current === controller) abortCtrlRef.current = null
      setIsLoading(false)
    }
  }

  // ── 初始化加载 ────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!sessionId) return

    ChatService.getSessionMessagesApiV1ChatSessionIdMessagesGet(sessionId)
      .then((res) => {
        const normalized: ChatResponse[] = res.map((msg) => ({
          id: msg.id,
          type: msg.type,
          content: normalizeContent(msg.content),
          parent_id: msg.parent_id ?? null,
          tool_calls: msg.tool_calls,
          files: msg.files,
          approval_status: msg.approval_status ?? null,
          usage_metadata: msg.usage_metadata ?? null,
        }))

        setAllMessages(normalized)

        // 初始激活路径：从根沿最后一个子节点走到叶子（即最新的对话链）
        const cm = buildChildrenMap(normalized)
        const defaultPath = getDefaultSubPath(null, cm)
        setActivePath(defaultPath)

        // Restore pending approval if the leaf AI message is still pending
        const pendingMsg = normalized.find(
          (m) => m.approval_status === 'pending' && defaultPath.includes(m.id)
        )
        if (pendingMsg) {
          setPendingApproval({
            messageId: pendingMsg.id,
            toolCalls: pendingMsg.tool_calls ?? [],
          })
        }
      })
      .catch((err) => console.error('加载聊天记录失败', err))
  }, [sessionId])

  // ── 发送消息 ──────────────────────────────────────────────────────────────

  const handleSendMessage = async (
    message: string,
    fileIds: number[] = [],
    files: ChatResponse['files'] = undefined
  ) => {
    if ((!message.trim() && fileIds.length === 0) || !sessionId || isLoading) return

    const lastId = activePath[activePath.length - 1] ?? null
    const newId = uuidv4()

    const humanMsg: ChatResponse = {
      id: newId,
      type: 'human',
      content: message,
      parent_id: lastId,
      files,
    }

    setAllMessages((prev) => [...prev, humanMsg])
    setActivePath((prev) => [...prev, newId])
    setIsLoading(true)

    await startChatStream(sessionId, {
      content: message,
      parent_id: lastId,
      id: newId,
      file_ids: fileIds,
    })
  }

  // ── 编辑消息 ──────────────────────────────────────────────────────────────

  const handleStartEdit = (messageId: string, currentContent: string) => {
    setEditingMessageId(messageId)
    setEditingContent(currentContent)
  }

  const handleCancelEdit = () => {
    setEditingMessageId(null)
    setEditingContent('')
  }

  const handleSaveEdit = async (messageId: string) => {
    if (!sessionId || !editingContent.trim()) return

    const msg = allMessages.find((m) => m.id === messageId)
    if (!msg) return

    const newId = uuidv4()
    const newHuman: ChatResponse = {
      id: newId,
      type: 'human',
      content: editingContent,
      parent_id: msg.parent_id ?? null, // 挂在同一父节点下，形成新分支
    }

    // 追加新节点到全量列表（原节点保留，形成分支）
    setAllMessages((prev) => [...prev, newHuman])

    // 激活路径：截到被编辑节点的上一位，再接新节点
    const splitIdx = activePath.indexOf(messageId)
    setActivePath([...activePath.slice(0, splitIdx), newId])

    setEditingMessageId(null)
    setEditingContent('')
    setIsLoading(true)

    await startChatStream(sessionId, {
      content: editingContent,
      parent_id: msg.parent_id ?? null,
      id: newId,
    })
  }

  // ── 重新生成 ──────────────────────────────────────────────────────────────

  const handleRegenerate = async (messageId: string) => {
    if (!sessionId || isLoading) return

    const msg = allMessages.find((m) => m.id === messageId)
    if (!msg) return

    // 激活路径截到该 AI 消息之前，等待流式新节点追加
    const splitIdx = activePath.indexOf(messageId)
    setActivePath(activePath.slice(0, splitIdx))
    setIsLoading(true)

    // content=null, id='' 告知后端重新生成
    await startChatStream(sessionId, {
      content: null,
      parent_id: msg.parent_id ?? null,
      id: '',
    })
  }

  // ── 切换兄弟节点 ──────────────────────────────────────────────────────────

  const handleSiblingSwitch = useCallback(
    (messageId: string, direction: 'prev' | 'next') => {
      const msg = allMessages.find((m) => m.id === messageId)
      if (!msg) return

      const cm = buildChildrenMap(allMessages)
      const siblings = cm.get(msg.parent_id ?? null) ?? []
      if (siblings.length <= 1) return

      const currentIdx = siblings.findIndex((m) => m.id === messageId)
      const newIdx = direction === 'prev' ? currentIdx - 1 : currentIdx + 1
      if (newIdx < 0 || newIdx >= siblings.length) return

      const target = siblings[newIdx]

      // 新路径 = 当前路径切到该节点位置之前 + 目标节点 + 目标节点往下的默认子路径
      const splitIdx = activePath.indexOf(messageId)
      const subPath = getDefaultSubPath(target.id, cm)

      setActivePath([...activePath.slice(0, splitIdx), target.id, ...subPath])
    },
    [allMessages, activePath]
  )

  // ── 工具审批 ──────────────────────────────────────────────────────────────

  const handleApproveTools = async (approved: boolean) => {
    if (!pendingApproval || !sessionId) return

    const { messageId } = pendingApproval
    setPendingApproval(null)
    setIsLoading(true)

    const baseUrl = getStreamBaseUrl()
    const token = tokenManager.getToken() ?? ''

    const controller = new AbortController()
    abortCtrlRef.current = controller

    try {
      const res = await fetch(`${baseUrl}/api/v1/chat/${sessionId}/approve-tool`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message_id: messageId, approved }),
        signal: controller.signal,
      })

      await processStream(res)
    } catch (error) {
      if ((error as Error)?.name !== 'AbortError') {
        console.error('Approve tool stream error:', error)
      }
    } finally {
      if (abortCtrlRef.current === controller) abortCtrlRef.current = null
      setIsLoading(false)
    }
  }

  // ── 压缩对话 ──────────────────────────────────────────────────────────────

  const handleCompress = useCallback(async () => {
    if (!sessionId || isCompressing || isLoading) return
    setIsCompressing(true)

    const baseUrl = getStreamBaseUrl()
    const token = tokenManager.getToken() ?? ''
    const controller = new AbortController()
    abortCtrlRef.current = controller

    const leafId = activePath[activePath.length - 1] ?? null
    let compressMsgId: string | null = null

    try {
      const res = await fetch(`${baseUrl}/api/v1/chat/${sessionId}/compress`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message_id: leafId }),
        signal: controller.signal,
      })

      if (!res.body) return
      await readSseStream(res.body, (eventType, dataLine) => {
        if (eventType === 'done') return true
        if (eventType === 'error') {
          const data = JSON.parse(dataLine) as { message?: string }
          setStreamError(data.message ?? '压缩失败')
          return true
        }
        try {
          const parsed = JSON.parse(dataLine) as { type?: string; data?: { id?: string; content?: unknown; parent_id?: string | null } }
          if (parsed.type !== 'AIMessageChunk') return false
          const chunk = parsed.data
          if (!chunk?.id) return false
          compressMsgId = chunk.id
          handleStreamChunk(chunk.id, 'AIMessageChunk', chunk.content, undefined, chunk.parent_id ?? null)
        } catch {
          /* ignore malformed chunk */
        }
        return false
      })

      // 流式完成后,把激活路径收敛为只剩压缩消息——它的 parent_id=null,
      // 等价于"开新会话",与后端 get_ancestor_chain 行为一致。
      if (compressMsgId) {
        const finalId = compressMsgId
        setActivePath([finalId])
        // 补一下 name 标记,刷新前与刷新后语义一致
        setAllMessages((prev) =>
          prev.map((m) => (m.id === finalId ? { ...m, name: '__compressed__' } : m))
        )
      }
    } catch (err) {
      if ((err as Error)?.name !== 'AbortError') {
        console.error('压缩失败', err)
      }
    } finally {
      if (abortCtrlRef.current === controller) abortCtrlRef.current = null
      setIsCompressing(false)
    }
  }, [sessionId, activePath, isCompressing, isLoading])

  // ─────────────────────────────────────────────────────────────────────────

  const clearStreamError = useCallback(() => setStreamError(null), [])

  return {
    displayMessages,
    isLoading,
    isCompressing,
    editingMessageId,
    editingContent,
    pendingApproval,
    streamError,
    setEditingContent,
    handleSendMessage,
    handleApproveTools,
    handleCompress,
    handleStartEdit,
    handleCancelEdit,
    handleSaveEdit,
    handleRegenerate,
    handleSiblingSwitch,
    getSiblingInfo,
    clearStreamError,
    stopStream,
  }
}
