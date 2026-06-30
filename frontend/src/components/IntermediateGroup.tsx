import React from 'react'
import { ChevronDown, ChevronRight, Wrench } from 'lucide-react'
import type { ChatResponse } from '../api'

interface IntermediateGroupProps {
  messages: ChatResponse[]
  expanded: boolean
  onToggle: () => void
  renderMessage: (msg: ChatResponse) => React.ReactNode
}

const extractToolNames = (messages: ChatResponse[]): string[] => {
  const names = new Set<string>()
  for (const msg of messages) {
    if (Array.isArray(msg.tool_calls)) {
      for (const tc of msg.tool_calls) {
        if (tc && typeof tc.name === 'string' && tc.name) names.add(tc.name)
      }
    }
    if (msg.type === 'tool' && typeof msg.name === 'string' && msg.name) {
      names.add(msg.name)
    }
  }
  return Array.from(names)
}

const IntermediateGroup: React.FC<IntermediateGroupProps> = ({
  messages,
  expanded,
  onToggle,
  renderMessage,
}) => {
  const toolNames = extractToolNames(messages)
  const summary = toolNames.length > 0 ? toolNames.join(', ') : '工具调用'

  return (
    <div className="flex gap-4">
      <div className="w-10 h-10 bg-gray-200 dark:bg-zinc-700 rounded-2xl flex items-center justify-center text-gray-600 dark:text-zinc-300 flex-shrink-0">
        <Wrench size={18} />
      </div>
      <div className="flex-1 min-w-0">
        <button
          onClick={onToggle}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-cyan-400/30 bg-cyan-400/10 hover:bg-cyan-400/20 text-cyan-700 dark:text-cyan-300 text-sm transition-all max-w-full"
          title={expanded ? '收起中间过程' : '展开中间过程'}
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <span className="font-medium">{expanded ? '收起中间过程' : '显示中间过程'}</span>
          <span className="text-xs opacity-80">· {messages.length} 步</span>
          {!expanded && (
            <span className="text-xs opacity-70 truncate ml-1 min-w-0">· {summary}</span>
          )}
        </button>

        {expanded && (
          <div className="mt-4 space-y-6">
            {messages.map((msg) => (
              <React.Fragment key={msg.id}>{renderMessage(msg)}</React.Fragment>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default IntermediateGroup
