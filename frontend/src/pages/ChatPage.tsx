import React, { useState, useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import {
  Send,
  Bot,
  Loader2,
  Paperclip,
  X,
  MessageCirclePlus,
  Archive,
  Download,
  AlertCircle,
  Wrench,
  Share2,
  Copy,
  Check,
  Eye,
  EyeOff,
} from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import type {
  AgentFullOut,
  SimpleFile,
  MCPOut,
  ApiToolOut,
  ImageToolOut,
  BuiltinToolInfo,
  ChatResponse,
} from '../api'
import {
  AgentApiToolsService,
  AgentBuiltinToolsService,
  AgentImageToolsService,
  AgentMcpsService,
  AgentsService,
  ApiToolsService,
  BuiltinToolsService,
  ChatService,
  FilesService,
  ImageToolsService,
  McpService,
  SessionsService,
  SessionSharesService,
} from '../api'
import { CancelError } from '../api/core/CancelablePromise'
import { MessageBubble } from '../components/message'
import IntermediateGroup from '../components/IntermediateGroup'
import { useMessageHandler } from '../hooks/useMessageHandler'
import { useAppContext } from '../context/AppContext'
import ThemedSelect from '../components/ThemedSelect'
import WorkspaceFilesPanel from '../components/WorkspaceFilesPanel'
import { useHideIntermediatePref } from '../hooks/useUIPreferences'
import { writeToClipboard } from '../utils/clipboard'

type UploadStatus = 'uploading' | 'uploaded' | 'error' | 'cancelled'

interface PendingFile {
  localId: string
  file: File
  status: UploadStatus
  previewUrl?: string
  serverFileId?: number
  serverFile?: SimpleFile
  error?: string
  request?: { cancel: () => void }
}

const ChatPage: React.FC = () => {
  const { id: sessionId } = useParams<{ id: string }>()
  const [message, setMessage] = useState('')
  const navigate = useNavigate()
  const { refreshSessions } = useAppContext()

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [selectedAgent, setSelectedAgent] = useState<AgentFullOut>()
  const [selectedFiles, setSelectedFiles] = useState<PendingFile[]>([])
  const [enabledMCPCount, setEnabledMCPCount] = useState(0)
  const [isExporting, setIsExporting] = useState(false)
  const [shareModalOpen, setShareModalOpen] = useState(false)
  const [sharing, setSharing] = useState(false)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [shareCopied, setShareCopied] = useState(false)
  const [shareExpiresHours, setShareExpiresHours] = useState<number | ''>(24)

  // 中间过程消息显示偏好（全站默认 + 当前会话临时覆盖）
  const [hideIntermediatePref] = useHideIntermediatePref()
  const [overrideShowAll, setOverrideShowAll] = useState(false)
  const hideIntermediate = hideIntermediatePref && !overrideShowAll

  // 切换会话时复位临时覆盖
  useEffect(() => {
    setOverrideShowAll(false)
  }, [sessionId])

  // 输入框自动伸缩
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }, [message])

  // Tool panel state
  const [showToolPanel, setShowToolPanel] = useState(false)
  const [availableMcps, setAvailableMcps] = useState<MCPOut[]>([])
  const [availableApiTools, setAvailableApiTools] = useState<ApiToolOut[]>([])
  const [availableImageTools, setAvailableImageTools] = useState<ImageToolOut[]>([])
  const [availableBuiltinTools, setAvailableBuiltinTools] = useState<BuiltinToolInfo[]>([])
  const [enabledMcpIds, setEnabledMcpIds] = useState<number[]>([])
  const [enabledApiToolIds, setEnabledApiToolIds] = useState<number[]>([])
  const [enabledImageToolIds, setEnabledImageToolIds] = useState<number[]>([])
  const [enabledBuiltinTypes, setEnabledBuiltinTypes] = useState<string[]>([])
  const toolPanelRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [isDraggingOver, setIsDraggingOver] = useState(false)

  const createSessionWithCurrentAgent = async () => {
    if (!selectedAgent) {
      void navigate('/agents')
      return
    }

    try {
      const res = await SessionsService.createSessionApiV1SessionsPost({
        agent_id: selectedAgent.id,
        title: `与${selectedAgent.description || '助手'}的新会话`,
        is_active: true,
      })
      refreshSessions()
      void navigate(`/chat/${res.id}`)
    } catch (error) {
      console.error('创建会话失败:', error)
      toast.error('创建会话失败，请重试。')
    }
  }

  const hasSession = Boolean(sessionId)

  const {
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
  } = useMessageHandler({ sessionId })

  // ── 加载 session & agent ──────────────────────────────────────────────────

  useEffect(() => {
    if (!sessionId) return
    let cancelled = false

    const load = async () => {
      try {
        const session = await SessionsService.getSessionApiV1SessionsSessionIdGet(sessionId)
        if (!session) throw new Error('session not found')
        if (cancelled) return

        const agent = await AgentsService.getAgentApiV1AgentsAgentIdGet(session.agent_id)
        if (!cancelled) setSelectedAgent(agent)
      } catch (err) {
        console.error('加载会话失败', err)
        if (!cancelled) void navigate('/')
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [sessionId, navigate])

  useEffect(() => {
    if (!selectedAgent) return
    void Promise.all([
      McpService.listMcpsApiV1McpsGet(),
      ApiToolsService.listApiToolsApiV1ApiToolsGet(),
      ImageToolsService.listImageToolsApiV1ImageToolsGet(),
      BuiltinToolsService.listAvailableBuiltinToolsApiV1BuiltinToolsGet(),
      AgentMcpsService.listMcpsApiV1AgentsAgentIdMcpsGet(selectedAgent.id),
      AgentApiToolsService.listAgentToolsApiV1AgentsAgentIdApiToolsGet(selectedAgent.id),
      AgentImageToolsService.listAgentImageToolsApiV1AgentsAgentIdImageToolsGet(selectedAgent.id),
      AgentBuiltinToolsService.listAgentBuiltinToolsApiV1AgentsAgentIdBuiltinToolsGet(
        selectedAgent.id
      ),
    ]).then(
      ([
        allMcps,
        allApiTools,
        allImageTools,
        allBuiltins,
        mcpIds,
        apiToolIds,
        imageToolIds,
        builtinTypes,
      ]) => {
        setAvailableMcps(allMcps.filter((m) => m.is_enabled))
        setAvailableApiTools(allApiTools)
        setAvailableImageTools(allImageTools)
        setAvailableBuiltinTools(allBuiltins)
        setEnabledMcpIds(mcpIds)
        setEnabledApiToolIds(apiToolIds)
        setEnabledImageToolIds(imageToolIds)
        setEnabledBuiltinTypes(builtinTypes)
        setEnabledMCPCount(
          mcpIds.length + apiToolIds.length + imageToolIds.length + builtinTypes.length
        )
      }
    )
  }, [selectedAgent])

  // Close tool panel on outside click
  useEffect(() => {
    if (!showToolPanel) return
    const handler = (e: MouseEvent) => {
      if (toolPanelRef.current && !toolPanelRef.current.contains(e.target as Node)) {
        setShowToolPanel(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showToolPanel])

  const updateEnabledCount = (
    mcpIds: number[],
    apiIds: number[],
    imageIds: number[],
    builtinTypes: string[]
  ) => {
    setEnabledMCPCount(mcpIds.length + apiIds.length + imageIds.length + builtinTypes.length)
  }

  const toggleMcp = async (mcpId: number) => {
    if (!selectedAgent) return
    const newIds = enabledMcpIds.includes(mcpId)
      ? enabledMcpIds.filter((id) => id !== mcpId)
      : [...enabledMcpIds, mcpId]
    setEnabledMcpIds(newIds)
    updateEnabledCount(newIds, enabledApiToolIds, enabledImageToolIds, enabledBuiltinTypes)
    await AgentMcpsService.bindMcpsApiV1AgentsAgentIdMcpsPost(selectedAgent.id, newIds)
  }

  const toggleApiTool = async (toolId: number) => {
    if (!selectedAgent) return
    const newIds = enabledApiToolIds.includes(toolId)
      ? enabledApiToolIds.filter((id) => id !== toolId)
      : [...enabledApiToolIds, toolId]
    setEnabledApiToolIds(newIds)
    updateEnabledCount(enabledMcpIds, newIds, enabledImageToolIds, enabledBuiltinTypes)
    await AgentApiToolsService.syncAgentToolsApiV1AgentsAgentIdApiToolsPost(selectedAgent.id, {
      tool_ids: newIds,
    })
  }

  const toggleImageTool = async (toolId: number) => {
    if (!selectedAgent) return
    const newIds = enabledImageToolIds.includes(toolId)
      ? enabledImageToolIds.filter((id) => id !== toolId)
      : [...enabledImageToolIds, toolId]
    setEnabledImageToolIds(newIds)
    updateEnabledCount(enabledMcpIds, enabledApiToolIds, newIds, enabledBuiltinTypes)
    await AgentImageToolsService.syncAgentImageToolsApiV1AgentsAgentIdImageToolsPost(
      selectedAgent.id,
      { tool_ids: newIds }
    )
  }

  const toggleBuiltinTool = async (toolType: string) => {
    if (!selectedAgent) return
    const newTypes = enabledBuiltinTypes.includes(toolType)
      ? enabledBuiltinTypes.filter((t) => t !== toolType)
      : [...enabledBuiltinTypes, toolType]
    setEnabledBuiltinTypes(newTypes)
    updateEnabledCount(enabledMcpIds, enabledApiToolIds, enabledImageToolIds, newTypes)
    await AgentBuiltinToolsService.syncAgentBuiltinToolsApiV1AgentsAgentIdBuiltinToolsPost(
      selectedAgent.id,
      { tool_types: newTypes }
    )
  }

  // ── 自动滚动 ──────────────────────────────────────────────────────────────

  useEffect(() => {
    if (editingMessageId) return
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [displayMessages, editingMessageId])

  // ── 发送消息（带清空输入框） ──────────────────────────────────────────────

  const handleSendMessageWrapper = async () => {
    if (isLoading) return

    const uploadedFileIds = selectedFiles
      .filter((item) => item.status === 'uploaded' && item.serverFileId !== undefined)
      .map((item) => item.serverFileId!)

    const uploadedFiles = selectedFiles
      .filter((item) => item.status === 'uploaded' && item.serverFile)
      .map((item) => item.serverFile!)

    if (!message.trim() && uploadedFileIds.length === 0) return

    await handleSendMessage(message, uploadedFileIds, uploadedFiles)
    setMessage('')
    setSelectedFiles([])
  }

  const uploadSingleFile = (file: File) => {
    const localId = `${file.name}-${file.size}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const numericSessionId = sessionId ? Number(sessionId) : undefined
    const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
    const request = FilesService.uploadFileApiV1FilesPost(
      { file },
      Number.isFinite(numericSessionId) ? numericSessionId : undefined
    )

    setSelectedFiles((prev) => [
      ...prev,
      { localId, file, status: 'uploading', previewUrl, request },
    ])

    request
      .then((res) => {
        setSelectedFiles((prev) =>
          prev.map((item) =>
            item.localId === localId
              ? {
                  ...item,
                  status: 'uploaded',
                  serverFileId: res.id,
                  serverFile: {
                    id: res.id,
                    content_type: res.content_type,
                    url: res.url,
                  },
                  request: undefined,
                }
              : item
          )
        )
      })
      .catch((err) => {
        const isCancelled = err instanceof CancelError || err?.isCancelled
        setSelectedFiles((prev) =>
          prev.map((item) => {
            if (item.localId !== localId) return item
            if (isCancelled) return { ...item, status: 'cancelled', request: undefined }
            return { ...item, status: 'error', error: '上传失败', request: undefined }
          })
        )
      })
  }

  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return
    Array.from(files).forEach(uploadSingleFile)
  }

  const handleCancelUpload = (localId: string) => {
    setSelectedFiles((prev) => {
      const target = prev.find((item) => item.localId === localId)
      target?.request?.cancel()
      return prev
    })
  }

  const handleRemoveFile = (localId: string) => {
    setSelectedFiles((prev) => {
      const target = prev.find((item) => item.localId === localId)
      target?.request?.cancel()
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl)
      return prev.filter((item) => item.localId !== localId)
    })
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    if (!isDraggingOver) setIsDraggingOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsDraggingOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDraggingOver(false)
    if (!isLoading) handleFileSelect(e.dataTransfer.files)
  }

  const handleExport = async () => {
    if (!sessionId || isExporting) return
    setIsExporting(true)
    try {
      const data = await ChatService.exportMessageChainApiV1ChatSessionIdExportGet(sessionId)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `chat-export-${sessionId}-${Date.now()}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('导出失败:', err)
      toast.error('导出失败，请重试。')
    } finally {
      setIsExporting(false)
    }
  }

  const openShareModal = () => {
    setShareUrl(null)
    setShareCopied(false)
    setShareExpiresHours(24)
    setShareModalOpen(true)
  }

  const handleCreateShare = async () => {
    if (!sessionId || sharing) return
    setSharing(true)
    try {
      const expires = shareExpiresHours === '' ? null : Number(shareExpiresHours)
      const res = await SessionSharesService.createShare(sessionId, {
        expires_in_hours: expires && expires > 0 ? expires : null,
      })
      setShareUrl(`${window.location.origin}/share/${res.slug}`)
    } catch (err) {
      console.error('创建分享失败:', err)
      toast.error('创建分享失败，请重试。')
    } finally {
      setSharing(false)
    }
  }

  const handleCopyShareUrl = async () => {
    if (!shareUrl) return
    try {
      await writeToClipboard(shareUrl)
      setShareCopied(true)
      setTimeout(() => setShareCopied(false), 1500)
    } catch (e) {
      console.error('复制分享链接失败:', e)
      toast.error('复制失败，请手动复制分享链接。')
    }
  }

  // ─────────────────────────────────────────────────────────────────────────

  return (
    <>
      {/* 顶部栏 */}
      <div className="min-h-20 bg-gray-50 dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between gap-4 px-6 py-4 shadow-sm">
        <div className="flex min-w-0 items-center gap-4">
          <div className="shrink-0 text-4xl">
            {hasSession ? selectedAgent?.avatar || '🤖' : '💬'}
          </div>
          <div className="min-w-0">
            <h1 className="truncate font-semibold text-xl text-gray-800">
              {hasSession ? selectedAgent?.description || '通用助手' : '请先创建/选择 Agent'}
            </h1>
            <p className="truncate text-sm text-gray-600">
              {hasSession
                ? (() => {
                    const totalTokens = displayMessages
                      .filter((m) => m.type === 'ai' && m.usage_metadata?.total_tokens)
                      .reduce((acc, m) => acc + (m.usage_metadata?.total_tokens ?? 0), 0)
                    return `${
                      selectedAgent?.llm
                        ? `${selectedAgent.llm.provider} - ${selectedAgent.llm.model_name}`
                        : 'GPT-4'
                    } · ${enabledMCPCount} 个工具已启用${totalTokens > 0 ? ` · ${totalTokens} tokens` : ''}`
                  })()
                : '当前还没有会话，请先创建/选择 Agent 并开始对话'}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {displayMessages.length > 0 && (
            <>
              {hideIntermediatePref && (
                <button
                  onClick={() => setOverrideShowAll((v) => !v)}
                  className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-200 dark:border-cyan-800 bg-gray-50 dark:bg-zinc-800 text-cyan-700 dark:text-cyan-300 transition-all hover:bg-cyan-50 dark:hover:bg-cyan-900/20"
                  title={overrideShowAll ? '收起中间过程（仅本会话）' : '展开中间过程（仅本会话）'}
                  aria-label="切换中间过程显示"
                >
                  {overrideShowAll ? <Eye size={16} /> : <EyeOff size={16} />}
                </button>
              )}
              <button
                onClick={handleExport}
                disabled={isExporting}
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-green-200 dark:border-green-800 bg-gray-50 dark:bg-zinc-800 text-green-700 dark:text-green-400 transition-all hover:bg-green-50 dark:hover:bg-green-900/20 disabled:cursor-not-allowed disabled:opacity-50"
                title="导出当前对话链为 JSON（OpenAI 格式）"
                aria-label="导出对话"
              >
                {isExporting ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Download size={16} />
                )}
              </button>
              <button
                onClick={openShareModal}
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-800 text-gray-600 dark:text-zinc-400 transition-all hover:bg-gray-100 dark:hover:bg-zinc-700"
                title="生成只读分享链接"
                aria-label="分享"
              >
                <Share2 size={16} />
              </button>
              <button
                onClick={handleCompress}
                disabled={isLoading || isCompressing}
                className="flex h-10 w-10 items-center justify-center rounded-xl border border-amber-400/30 bg-gray-50 dark:bg-zinc-900 text-amber-600 transition-all hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                title="将当前对话压缩为摘要，节省 Token"
                aria-label="压缩对话"
              >
                {isCompressing ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Archive size={16} />
                )}
              </button>
            </>
          )}
          <button
            onClick={createSessionWithCurrentAgent}
            className="flex h-10 items-center gap-1.5 whitespace-nowrap rounded-xl bg-gray-900 dark:bg-white px-4 text-sm font-medium text-white dark:text-gray-900 transition-all hover:opacity-90"
          >
            <MessageCirclePlus size={16} />
            开始新对话
          </button>
          <button
            onClick={() => navigate('/agents')}
            className="flex h-10 items-center gap-1.5 whitespace-nowrap rounded-xl border border-gray-200 dark:border-zinc-700 bg-gray-100 dark:bg-zinc-800 px-4 text-sm font-medium text-gray-800 transition-all hover:bg-gray-200 dark:hover:bg-zinc-600"
          >
            <Bot size={16} />
            切换 Agent
          </button>
        </div>
      </div>

      {/* 主体区域：左侧工作区文件面板 + 消息列表 */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {hasSession && sessionId && (
          <WorkspaceFilesPanel sessionId={sessionId} isLoading={isLoading} />
        )}
        <div className="flex-1 overflow-y-auto px-8 py-8">
          {hasSession ? (
            <div className="max-w-3xl mx-auto space-y-6">
              {(() => {
                const renderMessage = (msg: ChatResponse) => (
                  <MessageBubble
                    type={msg.type}
                    name={msg.name}
                    content={
                      typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
                    }
                    files={msg.files ?? undefined}
                    toolCalls={msg.tool_calls ?? undefined}
                    usageMetadata={msg.usage_metadata ?? undefined}
                    messageId={msg.id}
                    isEditing={editingMessageId === msg.id}
                    editingContent={editingContent}
                    onStartEdit={handleStartEdit}
                    onCancelEdit={handleCancelEdit}
                    onSaveEdit={handleSaveEdit}
                    onEditingContentChange={setEditingContent}
                    onRegenerate={handleRegenerate}
                    onSiblingSwitch={handleSiblingSwitch}
                    siblingInfo={getSiblingInfo(msg.id)}
                  />
                )

                const isIntermediate = (m: ChatResponse) =>
                  m.type === 'tool' ||
                  (m.type === 'ai' &&
                    m.name !== '__compressed__' &&
                    Array.isArray(m.tool_calls) &&
                    m.tool_calls.length > 0)

                const nodes: React.ReactNode[] = []
                let buffer: ChatResponse[] = []
                const flushBuffer = (isTrailing: boolean) => {
                  if (buffer.length === 0) return
                  if (hideIntermediate) {
                    const groupMessages = buffer
                    // 仍在流式过程中的最后一组：默认展开，便于观察 agent 工作
                    const defaultCollapsed = !(isLoading && isTrailing)
                    nodes.push(
                      <IntermediateGroup
                        key={`group-${nodes.length}-${groupMessages[0].id ?? ''}`}
                        messages={groupMessages}
                        defaultCollapsed={defaultCollapsed}
                        renderMessage={renderMessage}
                      />
                    )
                  } else {
                    for (const m of buffer) {
                      nodes.push(
                        <React.Fragment key={`msg-${nodes.length}-${m.id ?? ''}`}>
                          {renderMessage(m)}
                        </React.Fragment>
                      )
                    }
                  }
                  buffer = []
                }

                for (const msg of displayMessages) {
                  if (isIntermediate(msg)) {
                    buffer.push(msg)
                  } else {
                    flushBuffer(false)
                    nodes.push(
                      <React.Fragment key={`msg-${nodes.length}-${msg.id ?? ''}`}>
                        {renderMessage(msg)}
                      </React.Fragment>
                    )
                  }
                }
                flushBuffer(true)
                return nodes
              })()}

              {/* 加载指示器：三个 cyan 小点浮动 */}
              {isLoading && (
                <div className="flex items-center gap-1.5 pl-2 py-1">
                  <span
                    className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce"
                    style={{ animationDelay: '0ms', animationDuration: '900ms' }}
                  />
                  <span
                    className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce"
                    style={{ animationDelay: '150ms', animationDuration: '900ms' }}
                  />
                  <span
                    className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce"
                    style={{ animationDelay: '300ms', animationDuration: '900ms' }}
                  />
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          ) : (
            <div className="max-w-2xl mx-auto h-full flex items-center">
              <div className="w-full bg-gray-50 dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-xl p-10 text-center shadow-lg">
                <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg- text-white flex items-center justify-center">
                  <MessageCirclePlus size={24} />
                </div>
                <h3 className="text-2xl font-semibold text-gray-800 mb-3">
                  先创建一个 Agent 再开始聊天
                </h3>
                <p className="text-gray-600 mb-6">
                  你现在在纯聊天入口（/chat），还没有具体会话。请先去 Agents 页面创建或选择
                  Agent，然后再点击“开始对话”。
                </p>
                <button
                  onClick={() => navigate('/agents')}
                  className="px-6 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:shadow-lg transition-all font-medium"
                >
                  前往 Agents
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 输入区域 */}
      {hasSession && (
        <div className="bg-gray-50 dark:bg-zinc-900 border-t border-gray-200 dark:border-zinc-800 px-6 pt-4 pb-3">
          <div
            className={`max-w-3xl mx-auto transition-all ${isDraggingOver ? 'ring-2 ring-gray-400 dark:ring-zinc-500 rounded-xl bg-gray-100 dark:bg-zinc-800' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {/* 错误提示条 */}
            {streamError && (
              <div className="mb-4 flex items-center gap-3 px-4 py-3 bg-red-500/15 rounded-2xl border border-red-400/30 text-red-400">
                <AlertCircle size={16} className="flex-shrink-0" />
                <span className="text-sm flex-1">{streamError}</span>
                <button
                  onClick={clearStreamError}
                  className="p-1 hover:bg-red-400/20 rounded-lg transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {/* 工具审批卡片 */}
            {pendingApproval && (
              <div className="mb-4 bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-5">
                <p className="text-sm font-semibold text-gray-700 mb-3">
                  🔧 Agent 想要调用以下工具，是否批准？
                </p>
                <div className="border-t border-gray-200 dark:border-zinc-800 py-3 space-y-1">
                  {pendingApproval.toolCalls.length > 0 ? (
                    pendingApproval.toolCalls.map((tc, i) => (
                      <div
                        key={i}
                        className="text-xs font-mono text-gray-600 bg-gray-50 dark:bg-zinc-900 rounded-xl px-3 py-2"
                      >
                        <span className="font-semibold text-gray-800">{tc.name}</span>
                        {'args' in tc && (
                          <span className="text-gray-500">
                            (
                            {Object.entries(tc.args ?? {})
                              .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                              .join(', ')}
                            )
                          </span>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-gray-500">（无法获取工具参数详情）</p>
                  )}
                </div>
                <div className="border-t border-gray-200 dark:border-zinc-800 pt-3 flex justify-end gap-3">
                  <button
                    onClick={() => handleApproveTools(false)}
                    className="px-5 py-2 text-sm bg-gray-100 dark:bg-zinc-800 text-gray-800 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-600 transition-all border border-gray-200 dark:border-zinc-700"
                  >
                    拒绝
                  </button>
                  <button
                    onClick={() => handleApproveTools(true)}
                    className="px-5 py-2 text-sm bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-xl hover:shadow-lg transition-all"
                  >
                    批准
                  </button>
                </div>
              </div>
            )}

            {/* 拖放提示覆盖层 */}
            {isDraggingOver && (
              <div className="mb-3 flex items-center justify-center gap-2 px-4 py-4 bg-gray-100 dark:bg-zinc-800 border-2 border-dashed border-gray-300 dark:border-zinc-600 rounded-2xl text-gray-600 dark:text-zinc-300 text-sm font-medium">
                <Paperclip size={16} />
                松开以上传文件
              </div>
            )}

            {/* 文件预览 */}
            {selectedFiles.length > 0 && (
              <div className="mb-3 space-y-2">
                {selectedFiles.map((item) => (
                  <div
                    key={item.localId}
                    className="flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800"
                  >
                    {item.previewUrl ? (
                      <img
                        src={item.previewUrl}
                        alt={item.file.name}
                        className="w-10 h-10 object-cover rounded-lg flex-shrink-0 border border-gray-200 dark:border-zinc-800"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-gray-200 dark:bg-zinc-700 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Paperclip size={18} className="text-gray-500 dark:text-white" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
                        {item.file.name}
                      </p>
                      <p className="text-xs text-gray-400">
                        {(item.file.size / 1024).toFixed(2)} KB ·
                        {item.status === 'uploading' && ' 上传中'}
                        {item.status === 'uploaded' && ' 已上传'}
                        {item.status === 'cancelled' && ' 已取消'}
                        {item.status === 'error' && ` ${item.error || '上传失败'}`}
                      </p>
                    </div>
                    {item.status === 'uploading' ? (
                      <button
                        onClick={() => handleCancelUpload(item.localId)}
                        className="px-2 py-1 text-xs text-amber-300 hover:text-amber-200"
                      >
                        取消
                      </button>
                    ) : null}
                    <button
                      onClick={() => handleRemoveFile(item.localId)}
                      className="p-1.5 hover:bg-gray-50 dark:bg-zinc-900 rounded-lg transition-colors"
                    >
                      <X
                        size={18}
                        className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                      />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="relative flex gap-3 items-end" ref={toolPanelRef}>
              {/* 工具选择面板 */}
              {showToolPanel && (
                <div className="absolute bottom-full mb-3 left-0 w-80 max-h-[60vh] overflow-y-auto bg-white dark:bg-slate-800/60 rounded-xl border border-gray-200 dark:border-white/15 shadow-lg z-50 p-4 space-y-4">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-gray-800 dark:text-white">
                      工具选择
                    </span>
                    <span className="text-xs text-gray-500 dark:text-white/50">
                      {enabledMCPCount} 个已启用
                    </span>
                  </div>

                  {/* MCP 工具 */}
                  {availableMcps.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 dark:text-white/50 mb-2 px-1">
                        MCP 工具
                      </p>
                      <div className="space-y-1">
                        {availableMcps.map((mcp) => (
                          <label
                            key={mcp.id}
                            className="flex items-center gap-3 px-3 py-2.5 bg-gray-50 dark:bg-zinc-900 rounded-2xl border border-gray-100 dark:border-zinc-800/50 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={enabledMcpIds.includes(mcp.id)}
                              onChange={() => toggleMcp(mcp.id)}
                              className="w-4 h-4 rounded text-gray-600 dark:text-zinc-300 focus:ring-gray-400 dark:focus:ring-zinc-500 focus:ring-2"
                            />
                            <span className="text-sm text-gray-800 dark:text-white truncate">
                              {mcp.mcp_name}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* HTTP API 工具 */}
                  {availableApiTools.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 dark:text-white/50 mb-2 px-1">
                        HTTP API 工具
                      </p>
                      <div className="space-y-1">
                        {availableApiTools.map((tool) => (
                          <label
                            key={tool.id}
                            className="flex items-center gap-3 px-3 py-2.5 bg-gray-50 dark:bg-zinc-900 rounded-2xl border border-gray-100 dark:border-zinc-800/50 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={enabledApiToolIds.includes(tool.id)}
                              onChange={() => toggleApiTool(tool.id)}
                              className="w-4 h-4 rounded text-gray-600 dark:text-zinc-300 focus:ring-gray-400 dark:focus:ring-zinc-500 focus:ring-2"
                            />
                            <span className="text-sm text-gray-800 dark:text-white flex-1 truncate">
                              {tool.name}
                            </span>
                            {tool.method && (
                              <span className="text-xs text-gray-500 dark:text-white/60 bg-gray-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded-full shrink-0">
                                {tool.method}
                              </span>
                            )}
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 图像生成工具 */}
                  {availableImageTools.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 dark:text-white/50 mb-2 px-1">
                        图像生成工具
                      </p>
                      <div className="space-y-1">
                        {availableImageTools.map((tool) => (
                          <label
                            key={tool.id}
                            className="flex items-center gap-3 px-3 py-2.5 bg-gray-50 dark:bg-zinc-900 rounded-2xl border border-gray-100 dark:border-zinc-800/50 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={enabledImageToolIds.includes(tool.id)}
                              onChange={() => toggleImageTool(tool.id)}
                              className="w-4 h-4 rounded text-gray-600 dark:text-zinc-300 focus:ring-gray-400 dark:focus:ring-zinc-500 focus:ring-2"
                            />
                            <span className="text-sm text-gray-800 dark:text-white flex-1 truncate">
                              {tool.name}
                            </span>
                            <span className="text-xs text-gray-500 dark:text-white/60 bg-gray-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded-full shrink-0">
                              {tool.provider}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 内置工具 */}
                  {availableBuiltinTools.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 dark:text-white/50 mb-2 px-1">
                        内置工具
                      </p>
                      <div className="space-y-1">
                        {availableBuiltinTools.map((tool) => (
                          <label
                            key={tool.tool_type}
                            className="flex items-center gap-3 px-3 py-2.5 bg-gray-50 dark:bg-zinc-900 rounded-2xl border border-gray-100 dark:border-zinc-800/50 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={enabledBuiltinTypes.includes(tool.tool_type)}
                              onChange={() => toggleBuiltinTool(tool.tool_type)}
                              className="w-4 h-4 rounded text-gray-600 dark:text-zinc-300 focus:ring-gray-400 dark:focus:ring-zinc-500 focus:ring-2"
                            />
                            <div className="flex-1 min-w-0">
                              <span className="text-sm text-gray-800 dark:text-white block truncate">
                                {tool.name}
                              </span>
                              {tool.description && (
                                <span className="text-xs text-gray-500 dark:text-white/60 block truncate">
                                  {tool.description}
                                </span>
                              )}
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  {availableMcps.length === 0 &&
                    availableApiTools.length === 0 &&
                    availableImageTools.length === 0 &&
                    availableBuiltinTools.length === 0 && (
                      <p className="text-sm text-gray-500 dark:text-white/50 text-center py-2">
                        暂无可用工具
                      </p>
                    )}
                </div>
              )}

              {/* 工具开关按钮 */}
              <button
                onClick={() => setShowToolPanel((v) => !v)}
                className={`p-4 rounded-2xl transition-all border shadow-md ${
                  showToolPanel
                    ? 'bg-gray-200 dark:bg-zinc-700 border-gray-300 dark:border-zinc-600 text-gray-600 dark:text-zinc-400'
                    : 'bg-gray-50 dark:bg-zinc-900 border-gray-200 dark:border-zinc-800 text-gray-400 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-700'
                }`}
                title="管理工具"
              >
                <Wrench size={20} />
              </button>

              {/* 文件上传 */}
              <label className="p-4 bg-gray-50 dark:bg-zinc-900 rounded-2xl cursor-pointer hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all border border-gray-200 dark:border-zinc-800 shadow-md">
                <Paperclip size={20} className="text-gray-500 dark:text-gray-300" />
                <input
                  type="file"
                  className="hidden"
                  multiple
                  onChange={(e) => {
                    handleFileSelect(e.target.files)
                    e.currentTarget.value = ''
                  }}
                  disabled={isLoading}
                />
              </label>

              {/* 输入框 */}
              <div className="flex-1 bg-gray-50 dark:bg-zinc-900 rounded-xl px-5 py-4 focus-within:ring-2 focus-within:ring-cyan-400/50 border border-gray-200 dark:border-zinc-800 shadow-lg transition-all">
                <textarea
                  ref={textareaRef}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      void handleSendMessageWrapper()
                    }
                  }}
                  placeholder="输入消息... (Shift + Enter 换行)"
                  className="w-full bg-transparent resize-none outline-none text-sm text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 overflow-y-auto"
                  rows={1}
                  style={{ maxHeight: '200px' }}
                  disabled={isLoading}
                />
              </div>

              {/* 发送 / 停止 按钮 */}
              {isLoading ? (
                <button
                  onClick={stopStream}
                  className="group relative p-4 bg-gray-50 dark:bg-zinc-900 rounded-2xl border border-rose-400/40 hover:border-rose-400/70 hover:bg-rose-500/10 transition-all shadow-md"
                  title="停止生成"
                >
                  <span className="relative block w-5 h-5">
                    <span className="absolute inset-0 rounded-full bg-rose-500/30 animate-ping" />
                    <span className="absolute inset-1/2 -translate-x-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-sm bg-rose-400 group-hover:bg-rose-300 transition-colors" />
                  </span>
                </button>
              ) : (
                <button
                  onClick={handleSendMessageWrapper}
                  disabled={
                    !message.trim() && !selectedFiles.some((item) => item.status === 'uploaded')
                  }
                  className="p-4 bg- text-white rounded-2xl  hover:scale-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 shadow-lg"
                >
                  <Send size={20} />
                </button>
              )}
            </div>

            <p className="text-xs text-gray-500 mt-3 text-center">AI 可能会出错，请核实重要信息</p>
          </div>
        </div>
      )}

      {shareModalOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-50 dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 w-full max-w-md">
            <div className="flex items-center justify-between p-6 pb-4 border-b border-gray-200 dark:border-zinc-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg- rounded-2xl flex items-center justify-center">
                  <Share2 size={20} className="text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800">分享对话</h3>
              </div>
              <button
                onClick={() => setShareModalOpen(false)}
                className="p-2 hover:bg-black/10 rounded-xl transition"
              >
                <X size={20} />
              </button>
            </div>
            <div className="px-6 pb-6 pt-4 space-y-4">
              {!shareUrl ? (
                <>
                  <p className="text-sm text-gray-700 leading-relaxed">
                    生成只读链接，任何人无需登录即可查看本会话当前的对话记录。工具调用结果在分享视图中会被隐藏，请放心使用。
                  </p>
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-1 block">有效期</label>
                    <ThemedSelect
                      value={shareExpiresHours}
                      onChange={(value) => setShareExpiresHours(value === '' ? '' : Number(value))}
                      options={[
                        { value: 1, label: '1 小时' },
                        { value: 24, label: '24 小时' },
                        { value: 24 * 7, label: '7 天' },
                        { value: '', label: '永不过期' },
                      ]}
                      className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800"
                    />
                  </div>
                  <button
                    onClick={handleCreateShare}
                    disabled={sharing}
                    className="w-full py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:shadow-lg transition font-medium disabled:opacity-50"
                  >
                    {sharing ? '生成中…' : '生成链接'}
                  </button>
                </>
              ) : (
                <>
                  <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-800 dark:text-green-300 text-sm rounded-2xl px-4 py-3">
                    分享链接已生成，复制后发送给任何人即可只读查看。
                  </div>
                  <div className="flex items-center gap-2 bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800 px-3 py-2">
                    <code className="flex-1 text-xs text-gray-700 break-all">{shareUrl}</code>
                    <button
                      onClick={handleCopyShareUrl}
                      className="p-1.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition"
                    >
                      {shareCopied ? (
                        <Check size={14} className="text-emerald-600" />
                      ) : (
                        <Copy size={14} className="text-gray-700" />
                      )}
                    </button>
                  </div>
                  <button
                    onClick={() => setShareModalOpen(false)}
                    className="w-full py-2.5 bg-gray-200 dark:bg-zinc-700 hover:bg-white/40 text-gray-700 rounded-2xl transition font-medium"
                  >
                    完成
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default ChatPage
