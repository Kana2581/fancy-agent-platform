import React, { useEffect, useRef, useState, useCallback } from 'react'
import {
  FolderClosed,
  FolderOpen,
  ChevronLeft,
  Download,
  DownloadCloud,
  Loader2,
  FileText,
  AlertCircle,
  RefreshCw,
} from 'lucide-react'
import { WorkspacesService } from '../api'
import type { WorkspaceFileOut } from '../api'

interface Props {
  sessionId: string
  isLoading: boolean
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
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

const WorkspaceFilesPanel: React.FC<Props> = ({ sessionId, isLoading }) => {
  const [collapsed, setCollapsed] = useState(true)
  const [files, setFiles] = useState<WorkspaceFileOut[]>([])
  const [hasNew, setHasNew] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<number | null>(null)
  const [downloadingAll, setDownloadingAll] = useState(false)

  const seenIdsRef = useRef<Set<number>>(new Set())
  const prevLoadingRef = useRef(isLoading)

  const refresh = useCallback(
    async (markAsSeen: boolean) => {
      if (!sessionId) return
      setRefreshing(true)
      setError(null)
      try {
        const next = await WorkspacesService.listFiles(sessionId)
        setFiles(next)
        if (markAsSeen) {
          seenIdsRef.current = new Set(next.map((f) => f.file_id))
          setHasNew(false)
        } else {
          const fresh = next.some((f) => !seenIdsRef.current.has(f.file_id))
          if (fresh) setHasNew(true)
          // 即便没有新增，也补齐 seen 集合
          next.forEach((f) => seenIdsRef.current.add(f.file_id))
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载失败')
      } finally {
        setRefreshing(false)
      }
    },
    [sessionId]
  )

  // session 切换：重置 + 拉一次（视为初始已读）
  useEffect(() => {
    seenIdsRef.current = new Set()
    setHasNew(false)
    setFiles([])
    setError(null)
    if (sessionId) void refresh(true)
  }, [sessionId, refresh])

  // agent 流结束（isLoading: true → false）后重新拉一次，标记新增
  useEffect(() => {
    const wasLoading = prevLoadingRef.current
    prevLoadingRef.current = isLoading
    if (wasLoading && !isLoading && sessionId) {
      void refresh(false)
    }
  }, [isLoading, sessionId, refresh])

  // 展开时清掉新增提醒
  useEffect(() => {
    if (!collapsed && hasNew) {
      setHasNew(false)
      seenIdsRef.current = new Set(files.map((f) => f.file_id))
    }
  }, [collapsed, hasNew, files])

  const handleDownload = async (f: WorkspaceFileOut) => {
    if (downloadingId === f.file_id) return
    setDownloadingId(f.file_id)
    try {
      const { blob, filename } = await WorkspacesService.downloadFile(f.file_id, f.name)
      triggerBlobDownload(blob, f.name || filename)
    } catch (e) {
      setError(e instanceof Error ? e.message : '下载失败')
    } finally {
      setDownloadingId(null)
    }
  }

  const handleDownloadAll = async () => {
    if (downloadingAll || files.length === 0) return
    setDownloadingAll(true)
    setError(null)
    try {
      const { blob, filename } = await WorkspacesService.downloadAll(sessionId)
      triggerBlobDownload(blob, filename)
    } catch (e) {
      setError(e instanceof Error ? e.message : '打包下载失败')
    } finally {
      setDownloadingAll(false)
    }
  }

  if (collapsed) {
    return (
      <div className="flex-shrink-0 py-4 pl-3">
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className={`relative w-12 h-12 rounded-2xl border flex items-center justify-center transition shadow-sm ${
            hasNew
              ? 'bg-gray-200 dark:bg-zinc-700 border-gray-300 dark:border-zinc-600 text-gray-600 dark:text-zinc-400 ring-2 ring-gray-300 dark:ring-zinc-600'
              : 'bg-white dark:bg-zinc-900 border-gray-200 dark:border-zinc-700 text-gray-800 hover:bg-gray-100 dark:hover:bg-zinc-700'
          }`}
          title="展开工作区文件"
          aria-label="展开工作区文件"
        >
          <FolderClosed size={20} />
          {files.length > 0 && (
            <span
              className={`absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold flex items-center justify-center ${
                hasNew
                  ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
                  : 'bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-300'
              }`}
            >
              {files.length}
            </span>
          )}
        </button>
      </div>
    )
  }

  return (
    <div className="flex-shrink-0 w-60 py-4 pl-3 pr-2 flex flex-col min-h-0">
      <div className="flex-1 min-h-0 bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-gray-200 dark:border-zinc-800">
          <div className="flex items-center gap-2 min-w-0">
            <FolderOpen size={18} className="text-gray-600 dark:text-zinc-300 flex-shrink-0" />
            <span className="text-sm font-medium text-gray-800 truncate">工作区文件</span>
            <span className="text-xs text-gray-600">({files.length})</span>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              type="button"
              onClick={handleDownloadAll}
              disabled={downloadingAll || files.length === 0}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-700 text-gray-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
              title={files.length === 0 ? '暂无文件' : '打包下载全部'}
              aria-label="打包下载全部"
            >
              {downloadingAll ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <DownloadCloud size={14} />
              )}
            </button>
            <button
              type="button"
              onClick={() => refresh(true)}
              disabled={refreshing}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-700 text-gray-700 transition disabled:opacity-50"
              title="刷新"
              aria-label="刷新"
            >
              {refreshing ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <RefreshCw size={14} />
              )}
            </button>
            <button
              type="button"
              onClick={() => setCollapsed(true)}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-700 text-gray-700 transition"
              title="折叠"
              aria-label="折叠"
            >
              <ChevronLeft size={16} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1.5">
          {error && (
            <div className="px-3 py-2 rounded-lg bg-rose-500/15 border border-rose-400/30 text-xs text-rose-300 flex items-start gap-1.5">
              <AlertCircle size={12} className="flex-shrink-0 mt-0.5" />
              <span className="break-all">{error}</span>
            </div>
          )}
          {files.length === 0 && !refreshing && !error && (
            <div className="px-3 py-6 text-center text-xs text-gray-600">暂无文件</div>
          )}
          {files.map((f) => (
            <div
              key={f.file_id}
              className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 transition px-2.5 py-2 flex items-center gap-2"
            >
              <FileText size={16} className="text-gray-600 dark:text-zinc-300 flex-shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-xs text-gray-800 truncate" title={f.name}>
                  {f.name}
                </div>
                <div className="text-[10px] text-gray-600">{formatSize(f.size)}</div>
              </div>
              <button
                type="button"
                onClick={() => handleDownload(f)}
                disabled={downloadingId === f.file_id}
                className="flex-shrink-0 p-1.5 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 shadow hover:opacity-90 transition disabled:opacity-60 disabled:cursor-not-allowed"
                title="下载"
                aria-label={`下载 ${f.name}`}
              >
                {downloadingId === f.file_id ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Download size={12} />
                )}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default WorkspaceFilesPanel
