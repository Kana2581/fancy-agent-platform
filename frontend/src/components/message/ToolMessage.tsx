import React, { useState } from 'react'
import { ChevronDown, ChevronRight, Wrench } from 'lucide-react'
import { FilePresentCard, tryParseFilePresent } from '../FilePresentCard'

export const ToolMessage: React.FC<{ content: string }> = ({ content }) => {
  const [isExpanded, setIsExpanded] = useState(false)

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
