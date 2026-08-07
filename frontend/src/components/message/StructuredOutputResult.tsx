import React, { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import type { StructuredOutputArtifact, StructuredOutputField } from '../../api'
import { writeToClipboard } from '../../utils/clipboard'

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '未提取'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'bigint') return value.toString()
  return '未提取'
}

function isEmptyValue(value: unknown): boolean {
  return value === null || value === undefined || value === ''
}

function renderObjectArray(field: StructuredOutputField, value: unknown) {
  if (!Array.isArray(value) || value.length === 0) {
    return <span className="text-gray-400 italic">未提取</span>
  }
  const itemFields = field.item_fields ?? []
  if (!itemFields.length) {
    return <span className="whitespace-pre-wrap">{formatValue(value)}</span>
  }
  return (
    <div className="space-y-2">
      {value.map((item, index) => {
        const row = item && typeof item === 'object' && !Array.isArray(item)
          ? (item as Record<string, unknown>)
          : {}
        return (
          <div
            key={index}
            className="rounded-lg border border-gray-200 dark:border-zinc-700 overflow-hidden"
          >
            <div className="px-3 py-1.5 text-xs font-medium bg-gray-50 dark:bg-zinc-800 text-gray-500 dark:text-zinc-400">
              #{index + 1}
            </div>
            <div className="divide-y divide-gray-100 dark:divide-zinc-800">
              {itemFields.map((itemField) => {
                const itemValue = row[itemField.key]
                return (
                  <div
                    key={itemField.key}
                    className="grid grid-cols-[minmax(5.5rem,0.7fr)_minmax(0,1.5fr)] gap-3 px-3 py-2"
                  >
                    <div>
                      <div className="text-xs font-medium text-gray-600 dark:text-zinc-300">
                        {itemField.label}
                      </div>
                      <div className="text-[11px] text-gray-400 font-mono break-all">
                        {itemField.key}
                      </div>
                    </div>
                    <div
                      className={`text-sm whitespace-pre-wrap break-words ${
                        isEmptyValue(itemValue)
                          ? 'text-gray-400 italic'
                          : 'text-gray-900 dark:text-gray-100'
                      }`}
                    >
                      {formatValue(itemValue)}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export const StructuredOutputResult: React.FC<{ artifact: StructuredOutputArtifact }> = ({
  artifact,
}) => {
  const [copied, setCopied] = useState(false)

  const copyJson = async () => {
    await writeToClipboard(JSON.stringify(artifact.data, null, 2))
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="min-w-0 w-full sm:min-w-[30rem]">
      <div className="flex items-center justify-between gap-4 pb-3 border-b border-gray-200 dark:border-zinc-700">
        <div className="min-w-0">
          <div className="text-xs text-gray-500 dark:text-zinc-400">结构化结果</div>
          <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate">
            {artifact.schema_name ?? `Schema #${artifact.schema_id}`}
          </h3>
        </div>
        <button
          type="button"
          onClick={() => void copyJson()}
          title="复制 JSON"
          className="w-9 h-9 shrink-0 flex items-center justify-center rounded-lg border border-gray-200 dark:border-zinc-700 hover:bg-gray-100 dark:hover:bg-zinc-800"
        >
          {copied ? <Check size={16} /> : <Copy size={16} />}
        </button>
      </div>

      <div className="divide-y divide-gray-200 dark:divide-zinc-700">
        {artifact.schema_snapshot.fields.map((field) => {
          const value = artifact.data[field.key]
          const empty = isEmptyValue(value)
          return (
            <div key={field.key} className="grid grid-cols-[minmax(7rem,0.8fr)_minmax(0,1.5fr)] gap-4 py-3">
              <div>
                <div className="text-sm font-medium text-gray-700 dark:text-zinc-200">
                  {field.label}
                </div>
                <div className="text-xs text-gray-400 font-mono break-all">{field.key}</div>
              </div>
              <div
                className={`text-sm whitespace-pre-wrap break-words ${
                  empty ? 'text-gray-400 italic' : 'text-gray-900 dark:text-gray-100'
                }`}
              >
                {field.type === 'object_array' ? renderObjectArray(field, value) : formatValue(value)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
