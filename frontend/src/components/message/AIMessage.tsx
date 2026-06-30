import React, { useState } from 'react'
import { ChevronDown, ChevronRight, Wrench } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { ToolCallData } from './types'

function getToolCallKey(toolCall: ToolCallData, idx: number): string {
  if (typeof toolCall.id === 'string' && toolCall.id) return toolCall.id

  const name = typeof toolCall.name === 'string' && toolCall.name ? toolCall.name : 'tool-call'
  const args =
    toolCall.args && typeof toolCall.args === 'object' ? JSON.stringify(toolCall.args) : ''
  return `${name}:${idx}:${args}`
}

const ToolCall: React.FC<{ toolCall: ToolCallData }> = ({ toolCall }) => {
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

      {toolCalls && toolCalls.length > 0 && (
        <div className="space-y-2">
          {toolCalls.map((toolCall, idx) => (
            <ToolCall key={getToolCallKey(toolCall, idx)} toolCall={toolCall} />
          ))}
        </div>
      )}
    </div>
  )
}
