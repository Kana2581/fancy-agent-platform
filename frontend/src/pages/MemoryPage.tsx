import React, { useState, useEffect } from 'react'
import { Trash2, ArrowLeft, Brain, Plus, Pencil, X, Check } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { UserMemoryOut } from '../api'
import { UserMemoriesService } from '../api'
import ThemedSelect from '../components/ThemedSelect'

type MemoryTypeFilter = 'all' | 'core' | 'normal'

type MemoryForm = {
  key: string
  content: string
  memory_type: 'core' | 'normal'
  category: string
}

const emptyForm = (): MemoryForm => ({
  key: '',
  content: '',
  memory_type: 'normal',
  category: '',
})

const MemoryPage: React.FC = () => {
  const navigate = useNavigate()
  const [memories, setMemories] = useState<UserMemoryOut[]>([])
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<MemoryTypeFilter>('all')
  const [categoryFilter, setCategoryFilter] = useState('')

  // Modal state
  const [modalOpen, setModalOpen] = useState(false)
  const [editingKey, setEditingKey] = useState<string | null>(null) // null = create
  const [form, setForm] = useState<MemoryForm>(emptyForm())
  const [saving, setSaving] = useState(false)

  const loadMemories = async () => {
    setLoading(true)
    try {
      const data = await UserMemoriesService.listMemories(
        typeFilter === 'all' ? undefined : typeFilter,
        categoryFilter.trim() || undefined
      )
      setMemories(data)
    } catch (e) {
      console.error('加载记忆失败:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadMemories()
  }, [typeFilter, categoryFilter])

  const handleDelete = async (memory: UserMemoryOut) => {
    if (!confirm(`确定要删除记忆「${memory.key}」吗？`)) return
    try {
      await UserMemoriesService.deleteMemory(memory.key)
      setMemories((prev) => prev.filter((m) => m.id !== memory.id))
    } catch (e) {
      console.error(e)
      alert('删除失败')
    }
  }

  const openCreate = () => {
    setEditingKey(null)
    setForm(emptyForm())
    setModalOpen(true)
  }

  const openEdit = (memory: UserMemoryOut) => {
    setEditingKey(memory.key)
    setForm({
      key: memory.key,
      content: memory.content,
      memory_type: memory.memory_type,
      category: memory.category || '',
    })
    setModalOpen(true)
  }

  const handleSave = async () => {
    if (!form.key.trim() || !form.content.trim()) {
      alert('标识符和内容不能为空')
      return
    }
    setSaving(true)
    try {
      const saved = await UserMemoriesService.saveMemory({
        key: form.key.trim(),
        content: form.content.trim(),
        memory_type: form.memory_type,
        category: form.category.trim() || undefined,
      })
      setMemories((prev) => {
        const idx = prev.findIndex((m) => m.key === saved.key)
        if (idx >= 0) {
          const next = [...prev]
          next[idx] = saved
          return next
        }
        return [saved, ...prev]
      })
      setModalOpen(false)
    } catch (e) {
      console.error(e)
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const categories = Array.from(
    new Set(memories.map((m) => m.category).filter(Boolean))
  ) as string[]

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
            <h2 className="text-3xl font-bold text-gray-800">记忆管理</h2>
            <p className="text-sm text-gray-600 mt-1">
              核心记忆自动注入系统提示词 · 普通记忆需 Agent 主动查询
            </p>
          </div>
          <button
            onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-xl shadow hover:opacity-90 transition font-medium text-sm"
          >
            <Plus size={15} />
            新建记忆
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-6 flex-wrap">
          <div className="flex gap-1 bg-white dark:bg-zinc-900 rounded-2xl p-1 border border-gray-200 dark:border-zinc-800">
            {(['all', 'core', 'normal'] as MemoryTypeFilter[]).map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`px-4 py-1.5 rounded-xl text-sm font-medium transition-all ${
                  typeFilter === t
                    ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900 shadow'
                    : 'text-gray-700 hover:bg-gray-100 dark:hover:bg-zinc-700'
                }`}
              >
                {t === 'all' ? '全部' : t === 'core' ? '核心' : '普通'}
              </button>
            ))}
          </div>

          {categories.length > 0 && (
            <ThemedSelect
              value={categoryFilter}
              onChange={(v) => setCategoryFilter(v)}
              placeholder="所有分类"
              options={[
                { value: '', label: '所有分类' },
                ...categories.map((c) => ({ value: c, label: c })),
              ]}
              className="px-3 py-2 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl text-sm text-gray-700"
            />
          )}

          <span className="text-sm text-gray-500 ml-auto">{memories.length} 条记忆</span>
        </div>

        {/* Content */}
        {loading ? (
          <div className="text-center text-gray-500 py-16">加载中...</div>
        ) : memories.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">🧠</div>
            <p className="text-gray-600 mb-2">暂无记忆</p>
            <p className="text-sm text-gray-500">
              在 Agent 中开启「记忆管理」内置工具，Agent
              会自动存取长期记忆；也可点击右上角手动新建。
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {memories.map((memory) => (
              <div
                key={memory.id}
                className="bg-white dark:bg-zinc-900 rounded-xl p-6 border border-gray-200 dark:border-zinc-700 group  hover:scale-[1.02] transition-all flex flex-col"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0 flex items-center gap-2">
                    <Brain
                      size={16}
                      className={
                        memory.memory_type === 'core'
                          ? 'text-amber-500 shrink-0'
                          : 'text-gray-600 dark:text-zinc-300 shrink-0'
                      }
                    />
                    <h3 className="font-semibold text-base text-gray-800 truncate">{memory.key}</h3>
                  </div>
                  <div className="flex items-center gap-1.5 ml-2 shrink-0">
                    {memory.memory_type === 'core' ? (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-400/20 text-amber-600 border border-amber-400/30 font-medium">
                        核心
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 border border-gray-200 dark:border-zinc-700 font-medium">
                        普通
                      </span>
                    )}
                    {memory.category && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-200 dark:bg-zinc-700 text-gray-700 dark:text-zinc-300 border border-cyan-400/30 font-medium">
                        {memory.category}
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-sm text-gray-600 bg-black/5 rounded-xl px-3 py-2.5 line-clamp-4 mb-4 flex-1 whitespace-pre-wrap">
                  {memory.content}
                </p>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">
                    {new Date(memory.updated_at).toLocaleDateString('zh-CN')}
                  </span>
                  <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-all">
                    <button
                      onClick={() => openEdit(memory)}
                      className="p-1.5 bg-gray-100 dark:bg-zinc-800 hover:bg-blue-100 text-gray-500 hover:text-gray-700 dark:text-zinc-300 rounded-xl transition-all"
                      title="编辑"
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => handleDelete(memory)}
                      className="p-1.5 bg-gray-100 dark:bg-zinc-800 hover:bg-red-100 text-gray-500 hover:text-red-600 rounded-xl transition-all"
                      title="删除"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-gray-50 dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 w-full max-w-lg">
            {/* Modal header */}
            <div className="sticky top-0 bg-gray-50 dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between p-6 pb-4 rounded-t-3xl">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg- rounded-2xl flex items-center justify-center">
                  <Brain size={20} className="text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800">
                  {editingKey ? '编辑记忆' : '新建记忆'}
                </h3>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="p-2 hover:bg-black/10 rounded-xl transition"
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal body */}
            <div className="px-6 pb-6 space-y-4">
              {/* Key */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  标识符 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={form.key}
                  onChange={(e) => setForm((f) => ({ ...f, key: e.target.value }))}
                  disabled={!!editingKey}
                  placeholder="如：用户偏好_语言"
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 transition-all disabled:opacity-50 text-sm"
                />
              </div>

              {/* memory_type */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">记忆级别</label>
                <div className="flex gap-2">
                  {(['normal', 'core'] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setForm((f) => ({ ...f, memory_type: t }))}
                      className={`flex-1 py-2 rounded-2xl text-sm font-medium transition-all border ${
                        form.memory_type === t
                          ? t === 'core'
                            ? 'bg-amber-400/20 text-amber-700 border-amber-400/40'
                            : 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700'
                          : 'bg-gray-100 dark:bg-zinc-800 text-gray-500 border-gray-200 dark:border-zinc-700 hover:bg-gray-200 dark:hover:bg-zinc-600'
                      }`}
                    >
                      {t === 'core' ? '核心（自动注入）' : '普通（按需查询）'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Category */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">分类（可选）</label>
                <input
                  type="text"
                  value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                  placeholder="如：偏好、工作、生活"
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 transition-all text-sm"
                />
              </div>

              {/* Content */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  内容 <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={form.content}
                  onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
                  rows={5}
                  placeholder="记忆的详细内容…"
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 resize-none transition-all text-sm"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setModalOpen(false)}
                  className="flex-1 py-2.5 bg-gray-200 dark:bg-zinc-700 hover:bg-white/40 text-gray-700 rounded-2xl text-sm font-medium transition-all"
                >
                  取消
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl text-sm font-medium hover:shadow-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Check size={15} />
                  {saving ? '保存中…' : '保存'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MemoryPage
