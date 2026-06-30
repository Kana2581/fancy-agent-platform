import React, { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { Plus, Edit2, Trash2, ArrowLeft, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { ImageToolCreate, ImageToolOut } from '../api'
import { ImageToolsService } from '../api'
import ImageToolWizard from '../components/ImageToolWizard'

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'DALL-E',
  stability: 'Stability AI',
  siliconflow: '硅基流动',
  aliyun: '阿里云（千问）',
}

const PROVIDER_COLORS: Record<string, string> = {
  openai: 'bg-green-400/20 text-green-800 border-green-400/30',
  stability: 'bg-purple-400/20 text-gray-700 dark:text-zinc-300 border-purple-400/30',
  siliconflow:
    'bg-gray-100 text-gray-700 border-gray-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700',
  aliyun: 'bg-orange-400/20 text-orange-800 border-orange-400/30',
}

const ImageToolsPage: React.FC = () => {
  const navigate = useNavigate()
  const [tools, setTools] = useState<ImageToolOut[]>([])
  const [loading, setLoading] = useState(true)
  const [showWizard, setShowWizard] = useState(false)
  const [editingTool, setEditingTool] = useState<ImageToolOut | null>(null)

  const loadTools = async () => {
    try {
      const data = await ImageToolsService.listImageTools()
      setTools(data)
    } catch (e) {
      console.error('加载图像工具失败:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadTools()
  }, [])

  const openCreate = () => {
    setEditingTool(null)
    setShowWizard(true)
  }
  const openEdit = (tool: ImageToolOut) => {
    setEditingTool(tool)
    setShowWizard(true)
  }

  const handleSave = async (_data: ImageToolCreate) => {
    setShowWizard(false)
    await loadTools()
  }

  const handleDelete = async (tool: ImageToolOut) => {
    const displayName = `${PROVIDER_LABELS[tool.provider] ?? tool.provider}${tool.model ? ' / ' + tool.model : ''}`
    if (!confirm(`确定要删除「${displayName}」吗？`)) return
    try {
      await ImageToolsService.deleteImageTool(tool.id)
      setTools((prev) => prev.filter((t) => t.id !== tool.id))
    } catch (e) {
      console.error(e)
      toast.error('删除失败')
    }
  }

  return (
    <div className="p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 px-3 py-2 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-50 dark:bg-zinc-800/300 rounded-xl transition"
          >
            <ArrowLeft size={16} />
            返回
          </button>
          <div>
            <h2 className="text-3xl font-bold text-gray-800">文生图模型</h2>
            <p className="text-sm text-gray-600 mt-1">
              配置 DALL-E / Stability AI / 硅基流动 / 阿里云千问 文生图模型
            </p>
          </div>
          <button
            onClick={openCreate}
            className="px-5 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl   transition-all flex items-center gap-2 font-medium"
          >
            <Plus size={20} />
            添加模型
          </button>
        </div>

        {loading ? (
          <div className="text-center text-gray-500 py-16">加载中...</div>
        ) : tools.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">🎨</div>
            <p className="text-gray-600 mb-2">暂无文生图模型</p>
            <p className="text-sm text-gray-500">添加模型后，可在图像工作台中使用</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {tools.map((tool) => (
              <div
                key={tool.id}
                className="bg-white dark:bg-zinc-900 rounded-xl p-6 border border-gray-200 dark:border-zinc-700 group  hover:scale-[1.02] transition-all flex flex-col"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`text-xs px-2.5 py-1 rounded-full border font-medium ${PROVIDER_COLORS[tool.provider] ?? 'bg-gray-200 text-gray-700'}`}
                      >
                        {PROVIDER_LABELS[tool.provider] ?? tool.provider}
                      </span>
                    </div>
                    {tool.model && (
                      <h3 className="font-semibold text-base text-gray-800 truncate mt-1">
                        {tool.model}
                      </h3>
                    )}
                    {tool.description && (
                      <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">
                        {tool.description}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex gap-2 flex-wrap text-xs text-gray-600 mb-4">
                  {tool.default_size && (
                    <span className="bg-gray-100 dark:bg-zinc-800 px-2.5 py-1 rounded-full">
                      {tool.default_size}
                    </span>
                  )}
                  {tool.support_img2img && (
                    <span className="bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 px-2.5 py-1 rounded-full border border-gray-200 dark:border-zinc-700">
                      img2img
                    </span>
                  )}
                </div>

                <div className="mt-auto flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => openEdit(tool)}
                    className="flex-1 py-2 text-sm bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-xl transition-all flex items-center justify-center gap-1.5"
                  >
                    <Edit2 size={14} />
                    编辑
                  </button>
                  <button
                    onClick={() => handleDelete(tool)}
                    className="p-2 hover:bg-red-100/50 text-red-500 rounded-xl transition-all"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showWizard && (
        <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-50 dark:bg-zinc-900 rounded-xl w-full max-w-2xl max-h-[92vh] overflow-y-auto shadow-sm border border-gray-200 dark:border-zinc-700">
            <div className="sticky top-0 bg-gray-50 dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 px-6 py-4 flex items-center justify-between">
              <h3 className="text-xl font-semibold text-gray-800">
                {editingTool
                  ? `编辑模型：${PROVIDER_LABELS[editingTool.provider] ?? editingTool.provider}${editingTool.model ? ' / ' + editingTool.model : ''}`
                  : '添加文生图模型'}
              </h3>
              <button
                onClick={() => setShowWizard(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded-xl transition-all text-gray-600"
              >
                <X size={18} />
              </button>
            </div>
            <div className="p-6">
              <ImageToolWizard
                initialTool={editingTool ?? undefined}
                onSave={handleSave}
                onCancel={() => setShowWizard(false)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ImageToolsPage
