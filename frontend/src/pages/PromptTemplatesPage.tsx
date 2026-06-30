import React, { useState, useEffect } from 'react'
import { Plus, Edit2, Trash2, Copy, ArrowLeft, X, FileText } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { PromptTemplateOut, PromptTemplateCreate, PromptTemplateUpdate } from '../api'
import { PromptTemplatesService } from '../api'
import { writeToClipboard } from '../utils/clipboard'

interface TemplateFormData {
  name: string
  content: string
  description: string
  category: string
}

const DEFAULT_FORM: TemplateFormData = {
  name: '',
  content: '',
  description: '',
  category: '',
}

const PromptTemplatesPage: React.FC = () => {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<PromptTemplateOut[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<PromptTemplateOut | null>(null)
  const [form, setForm] = useState<TemplateFormData>(DEFAULT_FORM)
  const [saving, setSaving] = useState(false)
  const [copiedId, setCopiedId] = useState<number | null>(null)

  const loadTemplates = async () => {
    try {
      const data = await PromptTemplatesService.listPromptTemplates()
      setTemplates(data)
    } catch (e) {
      console.error('加载提示词模板失败:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadTemplates()
  }, [])

  const openCreate = () => {
    setEditingTemplate(null)
    setForm(DEFAULT_FORM)
    setShowModal(true)
  }

  const openEdit = (template: PromptTemplateOut) => {
    setEditingTemplate(template)
    setForm({
      name: template.name,
      content: template.content,
      description: template.description ?? '',
      category: template.category ?? '',
    })
    setShowModal(true)
  }

  const handleSave = async () => {
    if (!form.name.trim() || !form.content.trim()) return
    setSaving(true)
    try {
      const payload = {
        name: form.name.trim(),
        content: form.content.trim(),
        description: form.description.trim() || null,
        category: form.category.trim() || null,
      }
      if (editingTemplate) {
        const updated = await PromptTemplatesService.updatePromptTemplate(
          editingTemplate.id,
          payload as PromptTemplateUpdate
        )
        setTemplates((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
      } else {
        const created = await PromptTemplatesService.createPromptTemplate(
          payload as PromptTemplateCreate
        )
        setTemplates((prev) => [created, ...prev])
      }
      setShowModal(false)
    } catch (e) {
      console.error(e)
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (template: PromptTemplateOut) => {
    if (!confirm(`确定要删除模板「${template.name}」吗？`)) return
    try {
      await PromptTemplatesService.deletePromptTemplate(template.id)
      setTemplates((prev) => prev.filter((t) => t.id !== template.id))
    } catch (e) {
      console.error(e)
      alert('删除失败')
    }
  }

  const handleCopy = async (template: PromptTemplateOut) => {
    try {
      await writeToClipboard(template.content)
      setCopiedId(template.id)
      setTimeout(() => setCopiedId(null), 1500)
    } catch {
      alert('复制失败，请手动复制')
    }
  }

  return (
    <div className="p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 px-3 py-2 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-50 dark:bg-zinc-800/300 rounded-xl transition"
          >
            <ArrowLeft size={16} />
            返回
          </button>
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-800">提示词模板</h2>
            <p className="text-sm text-gray-600 mt-1">管理常用提示词，快速复用</p>
          </div>
          <button
            onClick={openCreate}
            className="px-5 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl   transition-all flex items-center gap-2 font-medium"
          >
            <Plus size={20} />
            新建模板
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="text-center text-gray-500 py-16">加载中...</div>
        ) : templates.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">📝</div>
            <p className="text-gray-600 mb-2">暂无提示词模板</p>
            <p className="text-sm text-gray-500">创建模板后可在聊天时快速套用</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {templates.map((template) => (
              <div
                key={template.id}
                className="bg-white dark:bg-zinc-900 rounded-xl p-6 border border-gray-200 dark:border-zinc-700 group  hover:scale-[1.02] transition-all flex flex-col"
              >
                {/* Title row */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-lg text-gray-800 truncate">
                      {template.name}
                    </h3>
                    {template.description && (
                      <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">
                        {template.description}
                      </p>
                    )}
                  </div>
                  {template.category && (
                    <span className="ml-2 shrink-0 text-xs px-2.5 py-1 rounded-full border font-medium bg-gray-200 dark:bg-zinc-700 text-gray-700 dark:text-zinc-300 border-gray-300 dark:border-zinc-600">
                      {template.category}
                    </span>
                  )}
                </div>

                {/* Content preview */}
                <p className="text-sm text-gray-600 bg-black/5 rounded-xl px-3 py-2.5 line-clamp-3 mb-4 flex-1">
                  {template.content}
                </p>

                {/* Actions */}
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => openEdit(template)}
                    className="flex-1 py-2 text-sm bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-xl transition-all flex items-center justify-center gap-1.5"
                  >
                    <Edit2 size={14} />
                    编辑
                  </button>
                  <button
                    onClick={() => handleCopy(template)}
                    title="复制内容"
                    className="p-2 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-xl transition-all"
                  >
                    {copiedId === template.id ? (
                      <span className="text-xs text-green-600 font-medium px-1">✓</span>
                    ) : (
                      <Copy size={14} />
                    )}
                  </button>
                  <button
                    onClick={() => handleDelete(template)}
                    title="删除"
                    className="p-2 bg-gray-100 dark:bg-zinc-800 hover:bg-red-100 text-gray-700 hover:text-red-600 rounded-xl transition-all"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-50 dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 w-full max-w-lg">
            {/* Modal header */}
            <div className="sticky top-0 bg-gray-50 dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between p-6 pb-4 rounded-t-3xl">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg- rounded-2xl flex items-center justify-center">
                  <FileText size={20} className="text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800">
                  {editingTemplate ? '编辑模板' : '新建提示词模板'}
                </h3>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-black/10 rounded-xl transition"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal body */}
            <div className="px-6 pb-6 space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="为模板起个名字"
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 transition-all"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">分类</label>
                <input
                  type="text"
                  value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                  placeholder="可选，如：翻译、写作、代码..."
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 transition-all"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">描述</label>
                <input
                  type="text"
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="可选，简短描述模板用途"
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 transition-all"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  提示词内容 <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={form.content}
                  onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
                  placeholder="输入提示词内容..."
                  rows={6}
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 resize-none transition-all"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-2.5 bg-gray-200 dark:bg-zinc-700 hover:bg-white/40 text-gray-700 rounded-2xl transition-all font-medium"
                >
                  取消
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving || !form.name.trim() || !form.content.trim()}
                  className="flex-1 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:shadow-lg transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? '保存中...' : '保存'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PromptTemplatesPage
