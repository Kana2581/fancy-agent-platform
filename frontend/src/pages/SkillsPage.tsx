import React, { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { Plus, Edit2, Trash2, ArrowLeft, X, Zap } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { SkillOut, SkillCreate, SkillUpdate } from '../api'
import { SkillsService } from '../api'

interface SkillFile {
  path: string
  content: string
}

interface SkillFormData {
  name: string
  content: string
  description: string
  category: string
  files: SkillFile[]
}

const DEFAULT_FORM: SkillFormData = {
  name: '',
  content: '',
  description: '',
  category: '',
  files: [],
}

const SkillsPage: React.FC = () => {
  const navigate = useNavigate()
  const [skills, setSkills] = useState<SkillOut[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingSkill, setEditingSkill] = useState<SkillOut | null>(null)
  const [form, setForm] = useState<SkillFormData>(DEFAULT_FORM)
  const [saving, setSaving] = useState(false)

  const [scopeFilter, setScopeFilter] = useState<'all' | 'user' | 'system' | 'session'>('all')

  const loadSkills = async (scope: 'all' | 'user' | 'system' | 'session' = 'all') => {
    try {
      setLoading(true)
      const data = await SkillsService.listSkills(undefined, undefined, undefined, scope)
      setSkills(data)
    } catch (e) {
      console.error('加载技能失败:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadSkills(scopeFilter)
  }, [scopeFilter])

  const openCreate = () => {
    setEditingSkill(null)
    setForm(DEFAULT_FORM)
    setShowModal(true)
  }

  const openEdit = (skill: SkillOut) => {
    setEditingSkill(skill)
    setForm({
      name: skill.name,
      content: skill.content,
      description: skill.description ?? '',
      category: skill.category ?? '',
      files: (skill.files ?? []).map((f) => ({ path: f.path, content: f.content })),
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
        files: form.files
          .filter((f) => f.path.trim())
          .map((f) => ({ path: f.path.trim(), content: f.content })),
      }
      if (editingSkill) {
        const updated = await SkillsService.updateSkill(editingSkill.id, payload as SkillUpdate)
        setSkills((prev) => prev.map((s) => (s.id === updated.id ? updated : s)))
      } else {
        const created = await SkillsService.createSkill(payload as SkillCreate)
        setSkills((prev) => [created, ...prev])
      }
      setShowModal(false)
    } catch (e) {
      console.error(e)
      toast.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (skill: SkillOut) => {
    if (!confirm(`确定要删除技能「${skill.name}」吗？`)) return
    try {
      await SkillsService.deleteSkill(skill.id)
      setSkills((prev) => prev.filter((s) => s.id !== skill.id))
    } catch (e) {
      console.error(e)
      toast.error('删除失败')
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
            <h2 className="text-3xl font-bold text-gray-800">技能管理</h2>
            <p className="text-sm text-gray-600 mt-1">
              创建技能后，在 Agent 中开启「技能工具」即可按需调用
            </p>
          </div>
          <button
            onClick={openCreate}
            className="px-5 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl   transition-all flex items-center gap-2 font-medium"
          >
            <Plus size={20} />
            新建技能
          </button>
        </div>

        {/* Scope 筛选 */}
        <div className="flex gap-2 mb-5">
          {(['all', 'user', 'system', 'session'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setScopeFilter(s)}
              className={`px-3 py-1.5 text-sm rounded-xl border transition ${
                scopeFilter === s
                  ? 'bg-gray-900 dark:bg-white border-gray-900 dark:border-white text-white dark:text-gray-900 font-medium'
                  : 'bg-white dark:bg-zinc-900 border-gray-200 dark:border-zinc-700 text-gray-700 hover:bg-gray-100 dark:hover:bg-zinc-700'
              }`}
            >
              {s === 'all'
                ? '全部'
                : s === 'user'
                  ? '我的'
                  : s === 'system'
                    ? '系统内置'
                    : '会话临时'}
            </button>
          ))}
        </div>

        {/* Content */}
        {loading ? (
          <div className="text-center text-gray-500 py-16">加载中...</div>
        ) : skills.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">⚡</div>
            <p className="text-gray-600 mb-2">暂无技能</p>
            <p className="text-sm text-gray-500">创建技能后，Agent 可在对话中按需查询并使用</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {skills.map((skill) => (
              <div
                key={skill.id}
                className="bg-white dark:bg-zinc-900 rounded-xl p-6 border border-gray-200 dark:border-zinc-700 group  hover:scale-[1.02] transition-all flex flex-col"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-lg text-gray-800 truncate">{skill.name}</h3>
                    {skill.description && (
                      <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">
                        {skill.description}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-1 ml-2 shrink-0">
                    {skill.scope && skill.scope !== 'user' && (
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                          skill.scope === 'system'
                            ? 'bg-amber-400/20 text-amber-700 border-amber-400/40'
                            : 'bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 border-gray-200 dark:border-zinc-700'
                        }`}
                      >
                        {skill.scope === 'system' ? '系统' : '会话'}
                      </span>
                    )}
                    {skill.category && (
                      <span className="text-xs px-2.5 py-1 rounded-full border font-medium bg-gray-200 dark:bg-zinc-700 text-gray-700 dark:text-zinc-300 border-gray-300 dark:border-zinc-600">
                        {skill.category}
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-sm text-gray-600 bg-black/5 rounded-xl px-3 py-2.5 line-clamp-3 mb-2 flex-1">
                  {skill.content}
                </p>

                {skill.files && skill.files.length > 0 && (
                  <div className="text-xs text-gray-500 mb-3">📎 {skill.files.length} 个文件</div>
                )}

                {skill.scope !== 'system' ? (
                  <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => openEdit(skill)}
                      className="flex-1 py-2 text-sm bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-xl transition-all flex items-center justify-center gap-1.5"
                    >
                      <Edit2 size={14} />
                      编辑
                    </button>
                    <button
                      onClick={() => handleDelete(skill)}
                      title="删除"
                      className="p-2 bg-gray-100 dark:bg-zinc-800 hover:bg-red-100 text-gray-700 hover:text-red-600 rounded-xl transition-all"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ) : (
                  <div className="text-xs text-gray-500 italic">系统内置技能，只读</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-50 dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 w-full max-w-lg">
            <div className="sticky top-0 bg-gray-50 dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between p-6 pb-4 rounded-t-3xl">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg- rounded-2xl flex items-center justify-center">
                  <Zap size={20} className="text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800">
                  {editingSkill ? '编辑技能' : '新建技能'}
                </h3>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-black/10 rounded-xl transition"
              >
                <X size={20} />
              </button>
            </div>

            <div className="px-6 pb-6 space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="如：代码审查专家、翻译助手..."
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 transition-all"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">分类</label>
                <input
                  type="text"
                  value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
                  placeholder="可选，如：开发、写作、分析..."
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 transition-all"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">描述</label>
                <input
                  type="text"
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="可选，简短描述技能用途"
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 transition-all"
                />
              </div>

              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  技能内容 <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={form.content}
                  onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
                  placeholder="描述该技能的能力、行为规范、使用方式等..."
                  rows={8}
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 text-gray-800 placeholder-gray-500 resize-none transition-all"
                />
              </div>

              {/* 技能文件：随包携带、可执行的脚本/模板 */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-sm font-medium text-gray-700">
                    技能文件 <span className="text-gray-400 font-normal">（脚本/模板，可选）</span>
                  </label>
                  <button
                    type="button"
                    onClick={() =>
                      setForm((f) => ({ ...f, files: [...f.files, { path: '', content: '' }] }))
                    }
                    className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 text-gray-700 rounded-lg transition"
                  >
                    <Plus size={12} />
                    添加文件
                  </button>
                </div>
                <p className="text-xs text-gray-500 mb-2">
                  agent 用 <code>use_skill</code> 把文件物化到工作区，再用{' '}
                  <code>python_exec(script=...)</code> 运行（仅预装库）。
                </p>
                <div className="space-y-3">
                  {form.files.map((file, idx) => (
                    <div
                      key={idx}
                      className="border border-gray-200 dark:border-zinc-700 rounded-xl p-3 bg-white dark:bg-zinc-800/50"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <input
                          type="text"
                          value={file.path}
                          onChange={(e) =>
                            setForm((f) => ({
                              ...f,
                              files: f.files.map((x, i) =>
                                i === idx ? { ...x, path: e.target.value } : x
                              ),
                            }))
                          }
                          placeholder="文件路径，如 profile.py 或 templates/a.txt"
                          className="flex-1 px-3 py-1.5 text-sm bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 text-gray-800 placeholder-gray-400"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            setForm((f) => ({ ...f, files: f.files.filter((_, i) => i !== idx) }))
                          }
                          title="移除文件"
                          className="p-1.5 bg-gray-100 dark:bg-zinc-800 hover:bg-red-100 text-gray-600 hover:text-red-600 rounded-lg transition"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                      <textarea
                        value={file.content}
                        onChange={(e) =>
                          setForm((f) => ({
                            ...f,
                            files: f.files.map((x, i) =>
                              i === idx ? { ...x, content: e.target.value } : x
                            ),
                          }))
                        }
                        placeholder="文件内容（脚本/模板文本）"
                        rows={5}
                        className="w-full px-3 py-2 text-sm font-mono bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-gray-300 text-gray-800 placeholder-gray-400 resize-y"
                      />
                    </div>
                  ))}
                </div>
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

export default SkillsPage
