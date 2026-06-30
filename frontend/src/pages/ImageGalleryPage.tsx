import React, { useState, useEffect, useCallback } from 'react'
import {
  ArrowLeft,
  Trash2,
  Download,
  ChevronLeft,
  ChevronRight,
  X,
  ImageIcon,
  Loader2,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { GeneratedImageOut } from '../api'
import { GeneratedImagesService } from '../api'

const PAGE_SIZE = 20

const PROVIDER_LABEL: Record<string, string> = {
  openai: 'DALL-E',
  stability: 'Stability AI',
  siliconflow: 'SiliconFlow',
}

const ImageGalleryPage: React.FC = () => {
  const navigate = useNavigate()

  const [images, setImages] = useState<GeneratedImageOut[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<GeneratedImageOut | null>(null)
  const [deleting, setDeleting] = useState(false)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const fetchImages = useCallback(async (pg: number) => {
    setLoading(true)
    try {
      const data = await GeneratedImagesService.listGeneratedImagesApiV1GeneratedImagesGet(
        pg,
        PAGE_SIZE
      )
      setImages(data.items)
      setTotal(data.total)
    } catch (e) {
      console.error('加载失败:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchImages(page)
  }, [page, fetchImages])

  const handleDelete = async (id: number) => {
    setDeleting(true)
    try {
      await GeneratedImagesService.deleteGeneratedImageApiV1GeneratedImagesRecordIdDelete(id)
      setSelected(null)
      // Refresh: if we deleted the last item on a non-first page, go back
      const newTotal = total - 1
      const newTotalPages = Math.max(1, Math.ceil(newTotal / PAGE_SIZE))
      const targetPage = page > newTotalPages ? newTotalPages : page
      setTotal(newTotal)
      if (targetPage !== page) {
        setPage(targetPage)
      } else {
        void fetchImages(page)
      }
    } catch (e) {
      console.error('删除失败:', e)
    } finally {
      setDeleting(false)
    }
  }

  const handleDownload = (img: GeneratedImageOut) => {
    const a = document.createElement('a')
    a.href = img.image_url
    a.download = `generated_${img.id}.png`
    a.click()
  }

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr)
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="p-6 overflow-y-auto h-full">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => navigate('/image-studio')}
            className="flex items-center gap-2 px-3 py-2 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-50 dark:bg-zinc-800/300 rounded-xl transition text-sm"
          >
            <ArrowLeft size={15} />
            返回
          </button>
          <div>
            <h2 className="text-2xl font-bold text-gray-800">生成历史</h2>
            <p className="text-xs text-gray-500 mt-0.5">共 {total} 张图片</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-32">
            <Loader2 size={28} className="animate-spin text-gray-500" />
          </div>
        ) : images.length === 0 ? (
          <div className="text-center py-32">
            <div className="w-20 h-20 rounded-xl bg-white dark:bg-zinc-900 border-2 border-dashed border-gray-200 dark:border-zinc-700 flex items-center justify-center mx-auto mb-4">
              <ImageIcon size={32} className="text-gray-400 opacity-50" />
            </div>
            <p className="text-gray-500 text-sm">暂无生成记录</p>
            <button
              onClick={() => navigate('/image-studio')}
              className="mt-4 px-5 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:shadow-lg transition-all text-sm"
            >
              去生成图片
            </button>
          </div>
        ) : (
          <>
            {/* Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {images.map((img) => (
                <div
                  key={img.id}
                  onClick={() => setSelected(img)}
                  className="bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden cursor-pointer hover:bg-gray-100 dark:hover:bg-zinc-700 hover:scale-[1.02] transition-all group"
                >
                  <div className="aspect-square overflow-hidden bg-gray-50 dark:bg-zinc-900">
                    <img
                      src={img.thumbnail_url}
                      alt={img.prompt}
                      className="w-full h-full object-cover"
                      loading="lazy"
                      onError={(e) => {
                        const t = e.currentTarget
                        if (!t.dataset.fallback) {
                          t.dataset.fallback = '1'
                          t.src = img.image_url ?? ''
                        } else {
                          t.style.display = 'none'
                        }
                      }}
                    />
                  </div>
                  <div className="p-2.5">
                    <p className="text-xs text-gray-700 truncate">{img.prompt}</p>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs text-gray-500">
                        {PROVIDER_LABEL[img.provider] || img.provider}
                        {img.model_name ? ' · ' + img.model_name : ''}
                      </span>
                      {img.is_img2img && (
                        <span className="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 rounded-md">
                          编辑
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">{formatDate(img.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3 mt-8">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-xl bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 disabled:opacity-30 transition-all"
                >
                  <ChevronLeft size={16} className="text-gray-700" />
                </button>
                <span className="text-sm text-gray-700">
                  {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-2 rounded-xl bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 disabled:opacity-30 transition-all"
                >
                  <ChevronRight size={16} className="text-gray-700" />
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Detail Modal */}
      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
          onClick={() => setSelected(null)}
        >
          <div
            className="bg-gray-100 dark:bg-zinc-800 rounded-xl border border-gray-200 dark:border-zinc-700 shadow-sm w-full max-w-2xl max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal header */}
            <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-zinc-800">
              <div>
                <span className="text-sm font-medium text-gray-800">
                  {PROVIDER_LABEL[selected.provider] || selected.provider}
                  {selected.model_name ? ' · ' + selected.model_name : ''}
                </span>
                {selected.is_img2img && (
                  <span className="ml-2 text-xs px-2 py-0.5 bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 rounded-lg">
                    图片编辑
                  </span>
                )}
                <p className="text-xs text-gray-500 mt-0.5">
                  {new Date(selected.created_at).toLocaleString('zh-CN')}
                </p>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded-xl transition"
              >
                <X size={18} className="text-gray-700" />
              </button>
            </div>

            {/* Image */}
            <div className="p-5">
              <div className="rounded-2xl overflow-hidden border border-gray-200 dark:border-zinc-800 shadow-lg mb-4">
                <img
                  src={selected.image_url}
                  alt={selected.prompt}
                  className="w-full object-contain"
                />
              </div>

              {/* Prompt */}
              <div className="space-y-3">
                <div className="p-3 bg-gray-50 dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800">
                  <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">提示词</p>
                  <p className="text-sm text-gray-800 leading-relaxed">{selected.prompt}</p>
                </div>

                {selected.revised_prompt && (
                  <div className="p-3 bg-gray-50 dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800">
                    <p className="text-xs text-gray-500 mb-1 uppercase tracking-wide">
                      AI 修订提示词
                    </p>
                    <p className="text-sm text-gray-700 leading-relaxed">
                      {selected.revised_prompt}
                    </p>
                  </div>
                )}

                {(selected.width || selected.height) && (
                  <p className="text-xs text-gray-500">
                    尺寸：{selected.width} × {selected.height}
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-3 mt-5">
                <button
                  onClick={() => handleDownload(selected)}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-xl transition-all text-sm"
                >
                  <Download size={15} />
                  下载
                </button>
                <button
                  onClick={() => handleDelete(selected.id)}
                  disabled={deleting}
                  className="flex items-center justify-center gap-2 px-5 py-2.5 bg-red-400/20 hover:bg-red-400/30 text-red-700 rounded-xl transition-all text-sm disabled:opacity-50"
                >
                  {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                  删除
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ImageGalleryPage
