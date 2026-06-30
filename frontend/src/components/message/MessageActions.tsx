import React, { useState } from 'react'
import toast from 'react-hot-toast'
import {
  Copy,
  Check,
  Edit2,
  X,
  RotateCw,
  ChevronLeft,
  ChevronRight as ChevronRightIcon,
} from 'lucide-react'
import { writeToClipboard } from '../../utils/clipboard'

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
      {type === 'human' && !isEditing && (
        <button
          onClick={onStartEdit}
          className="p-2 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition-all hover:scale-110"
          title="编辑消息"
        >
          <Edit2 size={16} className="text-gray-500 dark:text-zinc-400" />
        </button>
      )}

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

      {type === 'ai' && !isEditing && (
        <button
          onClick={onRegenerate}
          className="p-2 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition-all hover:scale-110"
          title="重新生成"
        >
          <RotateCw size={16} className="text-gray-500 dark:text-zinc-400" />
        </button>
      )}

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

export default MessageActions
