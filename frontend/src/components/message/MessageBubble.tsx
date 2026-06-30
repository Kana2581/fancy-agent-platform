import React, { useState } from 'react'
import { Bot, Wrench } from 'lucide-react'
import type { SimpleFile } from '../../api'
import { AIMessage } from './AIMessage'
import { HumanMessage } from './HumanMessage'
import { ToolMessage } from './ToolMessage'
import MessageActions from './MessageActions'
import type { ToolCallData, UsageMetadata } from './types'

export const MessageBubble: React.FC<{
  type: string
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
      {type === 'ai' && (
        <div className="w-10 h-10 bg-gray-200 dark:bg-zinc-700 rounded-2xl flex items-center justify-center text-gray-600 dark:text-zinc-300 flex-shrink-0">
          <Bot size={20} />
        </div>
      )}

      {type === 'tool' && (
        <div className="w-10 h-10 bg-gray-200 dark:bg-zinc-700 rounded-2xl flex items-center justify-center flex-shrink-0">
          <Wrench size={20} />
        </div>
      )}

      <div className="flex flex-col max-w-2xl relative">
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
    </div>
  )
}
