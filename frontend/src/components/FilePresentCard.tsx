import React, { useState } from 'react'
import { Download, FileText, AlertCircle, Loader2 } from 'lucide-react'
import { WorkspacesService } from '../api'

export interface PresentedFile {
  file_id?: number
  name?: string
  path?: string
  size?: number
  /** legacy field from older tool messages; intentionally ignored — see WorkspacesService.downloadFile */
  download_url?: string
  error?: string
}

interface FilePresentCardProps {
  files: PresentedFile[]
  title?: string
}

function formatSize(bytes?: number): string {
  if (!bytes || bytes < 0) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  // Revoke after a tick to let the click finish.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

const FileRow: React.FC<{ file: PresentedFile }> = ({ file: f }) => {
  const [loading, setLoading] = useState(false)
  const [rowError, setRowError] = useState<string | null>(null)
  const downloadable = !f.error && typeof f.file_id === 'number'

  const handleDownload = async () => {
    if (!downloadable || loading) return
    setLoading(true)
    setRowError(null)
    try {
      const { blob, filename } = await WorkspacesService.downloadFile(
        f.file_id as number,
        f.name || f.path || `file-${f.file_id}`
      )
      triggerBlobDownload(blob, f.name || filename)
    } catch (e) {
      setRowError(e instanceof Error ? e.message : '下载失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 transition px-3 py-2 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <FileText size={18} className="text-gray-600 dark:text-zinc-300 flex-shrink-0" />
        <div className="min-w-0">
          <div className="text-sm text-gray-800 truncate">{f.name || f.path || '未命名文件'}</div>
          {f.error ? (
            <div className="text-xs text-rose-400 flex items-center gap-1 mt-0.5">
              <AlertCircle size={12} /> {f.error}
            </div>
          ) : rowError ? (
            <div className="text-xs text-rose-400 flex items-center gap-1 mt-0.5">
              <AlertCircle size={12} /> {rowError}
            </div>
          ) : (
            <div className="text-xs text-gray-600">{formatSize(f.size)}</div>
          )}
        </div>
      </div>
      {downloadable && (
        <button
          type="button"
          onClick={handleDownload}
          disabled={loading}
          className="flex-shrink-0 px-3 py-1.5 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-xs font-medium shadow hover:opacity-90 transition flex items-center gap-1 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
          {loading ? '下载中' : '下载'}
        </button>
      )}
    </div>
  )
}

export const FilePresentCard: React.FC<FilePresentCardProps> = ({ files, title }) => {
  if (!files || files.length === 0) return null

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-700 p-3 space-y-2">
      <div className="flex items-center gap-2 text-sm text-gray-800 font-medium">
        <FileText size={16} className="text-gray-600 dark:text-zinc-300" />
        <span>{title || 'Agent 已为你生成以下文件'}</span>
      </div>
      <div className="space-y-2">
        {files.map((f, idx) => (
          <FileRow key={f.file_id ?? idx} file={f} />
        ))}
      </div>
    </div>
  )
}

/**
 * 检测一段工具消息内容是否是 ws_present 的输出。
 * 输入是字符串（来自 ToolMessage.content）。
 */
// eslint-disable-next-line react-refresh/only-export-components -- helper colocated with the card it parses for; dev-only Fast Refresh hint
export function tryParseFilePresent(content: string): {
  files: PresentedFile[]
  title?: string
} | null {
  if (!content || typeof content !== 'string') return null
  let parsed: unknown
  try {
    parsed = JSON.parse(content)
  } catch {
    return null
  }
  if (!parsed || typeof parsed !== 'object') return null
  const obj = parsed as { presented_files?: unknown; title?: unknown }
  if (!Array.isArray(obj.presented_files)) return null
  return {
    files: obj.presented_files as PresentedFile[],
    title: typeof obj.title === 'string' ? obj.title : undefined,
  }
}
