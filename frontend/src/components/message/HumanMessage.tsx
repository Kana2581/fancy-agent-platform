import React, { useState } from 'react'
import { FileText } from 'lucide-react'
import type { SimpleFile } from '../../api'
import type { TextAnnotation, ContentBlock } from './types'

const FileCard: React.FC<{ file: TextAnnotation }> = ({ file }) => {
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

function parseHumanContent(content: string): { texts: string[]; files: TextAnnotation[] } {
  let parsedContent: ContentBlock[]
  let isJson = false

  try {
    const result = JSON.parse(content)
    if (Array.isArray(result)) {
      parsedContent = result
      isJson = true
    } else {
      parsedContent = [result]
      isJson = true
    }
  } catch {
    parsedContent = []
  }

  if (!isJson) {
    return { texts: [content], files: [] }
  }

  const texts: string[] = []
  const files: TextAnnotation[] = []
  for (const block of parsedContent) {
    if (block.type !== 'text') continue
    if (block.annotations && block.annotations.length > 0) {
      for (const ann of block.annotations) {
        if (ann.type === 'citation') files.push(ann)
      }
      continue
    }
    if (block.text && block.text.trim()) texts.push(block.text)
  }

  return { texts, files }
}

export const HumanMessage: React.FC<{
  content: string
  files?: SimpleFile[]
  isEditing: boolean
  editingContent: string
  onEditingContentChange: (content: string) => void
}> = ({ content, files: attachedFiles = [], isEditing, editingContent, onEditingContentChange }) => {
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
      {texts.length > 0 && (
        <div className="whitespace-pre-wrap text-sm leading-relaxed text-white">
          {texts.map((text, idx) => (
            <div key={idx}>{text}</div>
          ))}
        </div>
      )}

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
