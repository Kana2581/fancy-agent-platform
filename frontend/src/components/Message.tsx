import React, { useState } from 'react'
import toast from 'react-hot-toast'
import {
  ChevronDown,
  ChevronRight,
  Wrench,
  Bot,
  Copy,
  FileText,
  Edit2,
  Check,
  X,
  RotateCw,
  ChevronLeft,
  ChevronRight as ChevronRightIcon,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { SimpleFile } from '../api'
import { FilePresentCard, tryParseFilePresent } from './FilePresentCard'
import { writeToClipboard } from '../utils/clipboard'

type TextAnnotation = {
  id: string
  type: 'citation'
  title: string
  cited_text: string
}

type ContentBlock = {
  id: string
  type: 'text'
  text: string
  annotations?: TextAnnotation[]
}

type ToolCallData = {
  id?: string
  name?: string
  args?: Record<string, unknown>
  [key: string]: unknown
}

type UsageMetadata = {
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  [key: string]: unknown
}

// 工具调用组件
export const ToolCall: React.FC<{ toolCall: ToolCallData }> = ({ toolCall }) => {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="mt-2 border border-gray-200 dark:border-zinc-800 rounded-lg overflow-hidden bg-gray-50 dark:bg-zinc-900">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Wrench size={14} className="text-gray-500 dark:text-zinc-400" />
          <span className="text-sm font-medium text-gray-800">{toolCall.name || 'Tool Call'}</span>
        </div>
        {isExpanded ? (
          <ChevronDown size={16} className="text-gray-500 dark:text-zinc-400" />
        ) : (
          <ChevronRight size={16} className="text-gray-500 dark:text-zinc-400" />
        )}
      </button>
      {isExpanded && (
        <div className="px-3 py-2 border-t border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-800/30">
          <pre className="text-xs text-gray-700 overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(toolCall, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

// 工具消息组件（可折叠）
export const ToolMessage: React.FC<{ content: string }> = ({ content }) => {
  const [isExpanded, setIsExpanded] = useState(false)

  // 优先识别 ws_present 输出，渲染为下载卡片
  const present = tryParseFilePresent(content)
  if (present) {
    return <FilePresentCard files={present.files} title={present.title} />
  }

  let parsedContent
  let isJson = false

  try {
    parsedContent = JSON.parse(content)
    isJson = true
  } catch {
    parsedContent = content
  }

  return (
    <div className="border border-gray-200 dark:border-zinc-800 rounded-lg overflow-hidden bg-gray-50 dark:bg-zinc-900">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Wrench size={16} className="text-gray-500 dark:text-zinc-400" />
          <span className="text-sm font-medium text-gray-800">工具执行结果</span>
        </div>
        {isExpanded ? (
          <ChevronDown size={16} className="text-gray-500 dark:text-zinc-400" />
        ) : (
          <ChevronRight size={16} className="text-gray-500 dark:text-zinc-400" />
        )}
      </button>
      {isExpanded && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-800/30">
          {isJson ? (
            <pre className="text-xs text-gray-700 overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(parsedContent, null, 2)}
            </pre>
          ) : (
            <div className="text-sm text-gray-700 whitespace-pre-wrap">{content}</div>
          )}
        </div>
      )}
    </div>
  )
}

// AI 消息组件（支持 Markdown）
export const AIMessage: React.FC<{ content: string; toolCalls?: ToolCallData[] }> = ({
  content,
  toolCalls,
}) => {
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)
  return (
    <div className="space-y-2">
      {lightboxUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={() => setLightboxUrl(null)}
        >
          <div className="max-w-3xl max-h-[90vh] p-2" onClick={(e) => e.stopPropagation()}>
            <img
              src={lightboxUrl}
              alt="preview"
              className="max-w-full max-h-[85vh] rounded-2xl shadow-sm object-contain"
            />
          </div>
        </div>
      )}
      <div className="prose prose-sm max-w-none prose-invert">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '')
              const isInline = !(className && match)
              return !isInline && match ? (
                <SyntaxHighlighter
                  style={oneDark as { [key: string]: React.CSSProperties }}
                  language={match[1]}
                  PreTag="div"
                >
                  {/* eslint-disable-next-line @typescript-eslint/no-base-to-string -- children is string content in code blocks */}
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code
                  className="bg-gray-200 dark:bg-zinc-700 px-1.5 py-0.5 rounded text-gray-600 dark:text-zinc-300"
                  {...props}
                >
                  {children}
                </code>
              )
            },
            p: ({ children }) => <p className="mb-2 leading-relaxed text-gray-800">{children}</p>,
            ul: ({ children }) => (
              <ul className="list-disc list-inside space-y-1 text-gray-800">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-inside space-y-1 text-gray-800">{children}</ol>
            ),
            li: ({ children }) => <li className="text-gray-800">{children}</li>,
            h1: ({ children }) => (
              <h1 className="text-2xl font-bold mb-2 text-gray-900 dark:text-gray-100">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-xl font-bold mb-2 text-gray-900 dark:text-gray-100">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-lg font-bold mb-2 text-gray-900 dark:text-gray-100">
                {children}
              </h3>
            ),
            a: ({ children, href }) => (
              <a
                href={href}
                className="text-gray-600 dark:text-zinc-300 hover:text-gray-600 dark:text-zinc-300 underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                {children}
              </a>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-cyan-400 pl-4 italic text-gray-700">
                {children}
              </blockquote>
            ),
            table: ({ children }) => (
              <div className="overflow-x-auto my-2">
                <table className="min-w-full border border-gray-200 dark:border-zinc-800 rounded-lg text-sm">
                  {children}
                </table>
              </div>
            ),
            thead: ({ children }) => (
              <thead className="bg-gray-50 dark:bg-zinc-900">{children}</thead>
            ),
            tbody: ({ children }) => (
              <tbody className="divide-y divide-gray-200 dark:divide-zinc-700">{children}</tbody>
            ),
            tr: ({ children }) => (
              <tr className="hover:bg-gray-50 dark:hover:bg-zinc-800/30">{children}</tr>
            ),
            th: ({ children }) => (
              <th className="px-3 py-2 text-left font-semibold text-gray-800 dark:text-gray-100 border-b border-gray-200 dark:border-zinc-800">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="px-3 py-2 text-gray-700 dark:text-gray-200 border-r border-gray-100 dark:border-zinc-800/50 last:border-r-0">
                {children}
              </td>
            ),
            img: ({ src, alt }) =>
              src ? (
                <img
                  src={src}
                  alt={alt ?? ''}
                  className="max-w-full rounded-xl border border-gray-200 dark:border-zinc-800 my-2 cursor-pointer hover:opacity-90 transition-opacity"
                  onClick={() => setLightboxUrl(src)}
                />
              ) : null,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>

      {/* 渲染工具调用 */}
      {toolCalls && toolCalls.length > 0 && (
        <div className="space-y-2">
          {toolCalls.map((toolCall, idx) => (
            <ToolCall key={idx} toolCall={toolCall} />
          ))}
        </div>
      )}
    </div>
  )
}

// 文件卡片组件 - 优化版
export const FileCard: React.FC<{ file: TextAnnotation }> = ({ file }) => {
  return (
    <div className="mt-2 flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 hover:bg-white dark:hover:bg-zinc-800 transition-all">
      <div className="w-10 h-10 bg-gray-200 dark:bg-zinc-700 rounded-lg flex items-center justify-center flex-shrink-0">
        <FileText size={20} className="text-gray-500 dark:text-zinc-300" />
      </div>
      <div className="flex flex-col flex-1 min-w-0">
        <span className="text-sm font-medium text-gray-800 dark:text-zinc-200 truncate">
          {file.title}
        </span>
        <span className="text-xs text-gray-500 dark:text-zinc-400">已上传文件</span>
      </div>
    </div>
  )
}

const AttachedFileCard: React.FC<{ file: SimpleFile }> = ({ file }) => {
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)
  const fallbackName = file.url ? decodeURIComponent(file.url.split('/').pop() || '') : ''
  const title = fallbackName || `文件 #${file.id}`
  const isImage = file.content_type?.startsWith('image/')

  if (isImage && file.url) {
    return (
      <>
        <div
          className="mt-2 cursor-pointer rounded-xl overflow-hidden border border-gray-200 dark:border-zinc-800 hover:border-white/40 transition-all group"
          onClick={() => setLightboxUrl(file.url)}
        >
          <img
            src={file.url}
            alt={title}
            className="w-full max-h-48 object-cover group-hover:opacity-90 transition-opacity"
          />
          <div className="px-3 py-1.5 bg-gray-50 dark:bg-zinc-800/30">
            <p className="text-xs text-gray-400 truncate">{title}</p>
          </div>
        </div>
        {lightboxUrl && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
            onClick={() => setLightboxUrl(null)}
          >
            <div className="max-w-3xl max-h-[90vh] p-2" onClick={(e) => e.stopPropagation()}>
              <img
                src={lightboxUrl}
                alt={title}
                className="max-w-full max-h-[85vh] rounded-2xl shadow-sm object-contain"
              />
            </div>
          </div>
        )}
      </>
    )
  }

  return (
    <div className="mt-2 flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 hover:bg-white dark:hover:bg-zinc-800 transition-all">
      <div className="w-10 h-10 bg-gray-200 dark:bg-zinc-700 rounded-lg flex items-center justify-center flex-shrink-0">
        <FileText size={20} className="text-gray-500 dark:text-zinc-300" />
      </div>
      <div className="flex flex-col flex-1 min-w-0">
        <span className="text-sm font-medium text-gray-800 dark:text-zinc-200 truncate">
          {title}
        </span>
        {file.url ? (
          <a
            href={file.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-gray-600 dark:text-zinc-300 hover:text-gray-500 dark:text-zinc-400 truncate"
          >
            查看文件
          </a>
        ) : (
          <span className="text-xs text-gray-500 dark:text-zinc-400">文件 ID: {file.id}</span>
        )}
      </div>
    </div>
  )
}

// 解析人类消息内容
function parseHumanContent(content: string) {
  let parsedContent: ContentBlock[]
  let isJson = false

  try {
    const result = JSON.parse(content)

    if (Array.isArray(result)) {
      parsedContent = result // 安全赋值
      isJson = true
    } else {
      // 如果不是数组，可以包成数组或者报错
      parsedContent = [result]
      isJson = true
      // 或者 throw new Error('Expected array');
    }
  } catch {
    parsedContent = []
  }

  if (!isJson) {
    return {
      texts: [content],
      files: [] as TextAnnotation[],
    }
  }

  const texts: string[] = []
  const files: TextAnnotation[] = []
  for (const block of parsedContent) {
    if (block.type !== 'text') continue

    // 有 annotations → 文件
    if (block.annotations && block.annotations.length > 0) {
      for (const ann of block.annotations) {
        if (ann.type === 'citation') {
          files.push(ann)
        }
      }
      continue
    }

    // 没 annotations → 人说的话
    if (block.text && block.text.trim()) {
      texts.push(block.text)
    }
  }

  return { texts, files }
}

// 人类消息组件 - 支持编辑
export const HumanMessage: React.FC<{
  content: string
  files?: SimpleFile[]
  isEditing: boolean
  editingContent: string
  onEditingContentChange: (content: string) => void
}> = ({
  content,
  files: attachedFiles = [],
  isEditing,
  editingContent,
  onEditingContentChange,
}) => {
  const { texts, files } = parseHumanContent(content)

  if (isEditing) {
    return (
      <div className="space-y-2">
        <textarea
          value={editingContent}
          onChange={(e) => onEditingContentChange(e.target.value)}
          className="w-full bg-white dark:bg-zinc-800 rounded-2xl px-4 py-3 text-sm text-gray-900 dark:text-zinc-100 placeholder-gray-400 border border-gray-200 dark:border-zinc-700 focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 outline-none resize-none"
          rows={3}
          autoFocus
        />
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {/* 渲染文本内容 */}
      {texts.length > 0 && (
        <div className="whitespace-pre-wrap text-sm leading-relaxed text-white">
          {texts.map((text, idx) => (
            <div key={idx}>{text}</div>
          ))}
        </div>
      )}

      {/* 文件展示 */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file) => (
            <FileCard key={file.id} file={file} />
          ))}
        </div>
      )}

      {attachedFiles.length > 0 &&
        (() => {
          const imageFiles = attachedFiles.filter((f) => f.content_type?.startsWith('image/'))
          const docFiles = attachedFiles.filter((f) => !f.content_type?.startsWith('image/'))
          return (
            <div className="space-y-2">
              {imageFiles.length > 0 && (
                <div className={imageFiles.length === 1 ? '' : 'grid grid-cols-2 gap-2'}>
                  {imageFiles.map((file) => (
                    <AttachedFileCard key={file.id} file={file} />
                  ))}
                </div>
              )}
              {docFiles.map((file) => (
                <AttachedFileCard key={file.id} file={file} />
              ))}
            </div>
          )
        })()}
    </div>
  )
}

// 消息操作按钮组件
const MessageActions: React.FC<{
  type: string
  isEditing: boolean
  isHovered: boolean
  content: string
  onStartEdit?: () => void
  onCancelEdit?: () => void
  onSaveEdit?: () => void
  onRegenerate?: () => void
  onLoadSiblings?: () => void
  onSiblingSwitch?: (direction: 'prev' | 'next') => void
  siblingInfo?: { total: number; current: number }
}> = ({
  type,
  isEditing,
  isHovered,
  content,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onRegenerate,
  onLoadSiblings,
  onSiblingSwitch,
  siblingInfo,
}) => {
  const [copied, setCopied] = useState(false)
  React.useEffect(() => {
    if (isHovered && onLoadSiblings) {
      onLoadSiblings()
    }
  }, [isHovered, onLoadSiblings])
  const handleCopy = async () => {
    try {
      await writeToClipboard(content)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1200)
    } catch (err) {
      console.error('复制失败', err)
      toast.error('复制失败，请手动复制。')
    }
  }
  return (
    <div
      className={`flex items-center gap-1 transition-opacity duration-200 ${
        isHovered || isEditing ? 'opacity-100' : 'opacity-0 pointer-events-none'
      }`}
    >
      {/* 复制按钮 */}
      {!isEditing && (
        <button
          onClick={handleCopy}
          className="p-2 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition-all hover:scale-110"
          title={copied ? '已复制' : '复制消息'}
        >
          {copied ? (
            <Check size={16} className="text-green-500" />
          ) : (
            <Copy size={16} className="text-gray-500 dark:text-zinc-400" />
          )}
        </button>
      )}
      {/* Human 消息的编辑按钮 */}
      {type === 'human' && !isEditing && (
        <button
          onClick={onStartEdit}
          className="p-2 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition-all hover:scale-110"
          title="编辑消息"
        >
          <Edit2 size={16} className="text-gray-500 dark:text-zinc-400" />
        </button>
      )}

      {/* 编辑模式的保存和取消按钮 */}
      {type === 'human' && isEditing && (
        <>
          <button
            onClick={onSaveEdit}
            className="p-2 hover:bg-green-500/30 rounded-lg transition-all hover:scale-110"
            title="保存"
          >
            <Check size={16} className="text-green-400" />
          </button>
          <button
            onClick={onCancelEdit}
            className="p-2 hover:bg-red-500/30 rounded-lg transition-all hover:scale-110"
            title="取消"
          >
            <X size={16} className="text-red-400" />
          </button>
        </>
      )}

      {/* AI 消息的重新生成按钮 */}
      {type === 'ai' && !isEditing && (
        <button
          onClick={onRegenerate}
          className="p-2 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition-all hover:scale-110"
          title="重新生成"
        >
          <RotateCw size={16} className="text-gray-500 dark:text-zinc-400" />
        </button>
      )}

      {/* 切换消息按钮 */}
      {(type === 'human' || type === 'ai') &&
        !isEditing &&
        siblingInfo &&
        siblingInfo.total > 1 && (
          <div className="flex items-center gap-0.5 ml-1 bg-gray-50 dark:bg-zinc-900 rounded-lg px-1.5 py-1">
            <button
              onClick={() => onSiblingSwitch?.('prev')}
              disabled={siblingInfo.current <= 1}
              className="p-1 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded transition-all hover:scale-110 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100"
              title="上一条"
            >
              <ChevronLeft size={14} className="text-gray-500 hover:text-gray-300" />
            </button>

            <span className="text-xs px-2 font-medium text-gray-500">
              {siblingInfo.current} / {siblingInfo.total}
            </span>

            <button
              onClick={() => onSiblingSwitch?.('next')}
              disabled={siblingInfo.current >= siblingInfo.total}
              className="p-1 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded transition-all hover:scale-110 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:scale-100"
              title="下一条"
            >
              <ChevronRightIcon size={14} className={'text-gray-500'} />
            </button>
          </div>
        )}
    </div>
  )
}

// 消息气泡组件
export const MessageBubble: React.FC<{
  type: string
  name?: string | null
  content: string
  files?: SimpleFile[]
  toolCalls?: ToolCallData[]
  usageMetadata?: UsageMetadata | null
  messageId?: string
  isEditing?: boolean
  editingContent?: string
  onStartEdit?: (messageId: string, content: string) => void
  onCancelEdit?: () => void
  onSaveEdit?: (messageId: string) => void
  onEditingContentChange?: (content: string) => void
  onRegenerate?: (messageId: string) => void
  onLoadSiblings?: (messageId: string) => void
  onSiblingSwitch?: (messageId: string, direction: 'prev' | 'next') => void
  siblingInfo?: { total: number; current: number }
}> = ({
  type,
  content,
  files,
  toolCalls,
  usageMetadata,
  messageId,
  isEditing = false,
  editingContent = '',
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onEditingContentChange,
  onRegenerate,
  onLoadSiblings,
  onSiblingSwitch,
  siblingInfo,
}) => {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <div
      className={`flex gap-4 ${type === 'human' ? 'justify-end' : ''}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* AI 头像 */}
      {type === 'ai' && (
        <div className="w-10 h-10 bg-gray-200 dark:bg-zinc-700 rounded-2xl flex items-center justify-center text-gray-600 dark:text-zinc-300 flex-shrink-0">
          <Bot size={20} />
        </div>
      )}

      {/* 工具头像 */}
      {type === 'tool' && (
        <div className="w-10 h-10 bg-gray-200 dark:bg-zinc-700 rounded-2xl flex items-center justify-center flex-shrink-0">
          <Wrench size={20} />
        </div>
      )}

      {/* 消息内容容器 */}
      <div className="flex flex-col max-w-2xl relative">
        {/* 消息气泡 */}
        <div
          className={`${
            type === 'human'
              ? 'bg-gray-900 dark:bg-zinc-800 shadow-lg'
              : 'bg-gray-50 dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 shadow-md'
          } rounded-xl px-5 py-4`}
        >
          {type === 'ai' && <AIMessage content={content} toolCalls={toolCalls} />}
          {type === 'human' && (
            <HumanMessage
              content={content}
              files={files}
              isEditing={isEditing}
              editingContent={editingContent}
              onEditingContentChange={onEditingContentChange || (() => {})}
            />
          )}
          {type === 'tool' && <ToolMessage content={content} />}
        </div>

        {/* 操作按钮 */}
        {messageId && (type === 'human' || type === 'ai') && (
          <div
            className={`flex items-center gap-2 ${type === 'human' ? 'justify-end' : 'justify-start'} mt-1`}
          >
            {type === 'ai' && usageMetadata?.output_tokens && (
              <span
                className="text-xs text-gray-400"
                title={`输入: ${usageMetadata.input_tokens ?? '?'} | 输出: ${usageMetadata.output_tokens} | 合计: ${usageMetadata.total_tokens ?? '?'}`}
              >
                ↑{usageMetadata.input_tokens ?? '?'} ↓{usageMetadata.output_tokens}
              </span>
            )}
            <MessageActions
              type={type}
              isEditing={isEditing}
              isHovered={isHovered}
              content={content}
              onStartEdit={() => onStartEdit?.(messageId, content)}
              onCancelEdit={onCancelEdit}
              onSaveEdit={() => onSaveEdit?.(messageId)}
              onRegenerate={() => onRegenerate?.(messageId)}
              onLoadSiblings={() => onLoadSiblings?.(messageId)}
              onSiblingSwitch={(direction) => onSiblingSwitch?.(messageId, direction)}
              siblingInfo={siblingInfo}
            />
          </div>
        )}
      </div>

      {/* 人类头像 */}
      {type === 'human' && (
        <div className="w-10 h-10 bg-gray-200 dark:bg-zinc-700 rounded-2xl flex items-center justify-center text-gray-600 dark:text-zinc-300 flex-shrink-0 font-semibold">
          U
        </div>
      )}
    </div>
  )
}
