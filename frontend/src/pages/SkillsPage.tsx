import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertCircle, ArrowLeft, FileText, Folder, RefreshCw } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import type { SkillFileContentOut, SkillOut, SkillTreeNode } from '../api'
import { SkillsService } from '../api'

const SkillsPage: React.FC = () => {
  const navigate = useNavigate()
  const [scope, setScope] = useState<'all' | 'user' | 'system'>('all')
  const [skills, setSkills] = useState<SkillOut[]>([])
  const [selected, setSelected] = useState<SkillOut | null>(null)
  const [tree, setTree] = useState<SkillTreeNode[]>([])
  const [preview, setPreview] = useState<SkillFileContentOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [treeLoading, setTreeLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectSkill = useCallback(async (skill: SkillOut) => {
    setSelected(skill)
    setTreeLoading(true)
    setPreview(null)
    try {
      const [nodes, content] = await Promise.all([
        SkillsService.listTree(skill.scope, skill.package_path),
        SkillsService.readFile(skill.scope, skill.package_path, 'SKILL.md'),
      ])
      setTree(nodes)
      setPreview(content)
    } catch (err) {
      console.error(err)
      setTree([])
      setPreview(null)
    } finally {
      setTreeLoading(false)
    }
  }, [])

  const loadSkills = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await SkillsService.listSkills(scope)
      setSkills(result)
    } catch (err) {
      console.error(err)
      setError('Skill 目录读取失败')
    } finally {
      setLoading(false)
    }
  }, [scope])

  const openFile = async (node: SkillTreeNode) => {
    if (!selected || node.type !== 'file') return
    try {
      setPreview(await SkillsService.readFile(selected.scope, selected.package_path, node.path))
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    void loadSkills()
  }, [loadSkills])

  useEffect(() => {
    if (selected && !skills.some(
      (item) => item.scope === selected.scope && item.package_path === selected.package_path
    )) {
      setSelected(null)
      setTree([])
      setPreview(null)
    }
  }, [skills, selected])

  const groupedTree = useMemo(() => {
    const groups = new Map<string, SkillTreeNode[]>()
    for (const node of tree) {
      const top = node.path.split('/')[0]
      const list = groups.get(top) ?? []
      list.push(node)
      groups.set(top, list)
    }
    return Array.from(groups.entries())
  }, [tree])

  return (
    <div className="p-8 overflow-y-auto h-full">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 px-3 py-2 bg-gray-200 dark:bg-zinc-700 rounded-xl"
          >
            <ArrowLeft size={16} />
            返回
          </button>
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-800">Skill 文件库</h2>
            <p className="text-sm text-gray-600 mt-1">文件系统是 Skill 的唯一来源，模型通过 Bash 使用</p>
          </div>
          <button
            onClick={() => void loadSkills()}
            title="刷新"
            className="p-2 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-700"
          >
            <RefreshCw size={18} />
          </button>
        </div>

        <div className="flex gap-2 mb-5">
          {(['all', 'user', 'system'] as const).map((item) => (
            <button
              key={item}
              onClick={() => setScope(item)}
              className={`px-3 py-1.5 text-sm rounded-xl border ${
                scope === item
                  ? 'bg-gray-900 text-white border-gray-900'
                  : 'bg-white border-gray-200 text-gray-700'
              }`}
            >
              {item === 'all' ? '全部' : item === 'user' ? '我的' : '系统'}
            </button>
          ))}
        </div>

        {error && <div className="mb-4 text-sm text-red-600">{error}</div>}

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(280px,360px)_1fr] gap-5 min-h-[560px]">
          <div className="space-y-2">
            {loading ? (
              <div className="text-gray-500 py-10 text-center">扫描中...</div>
            ) : skills.length === 0 ? (
              <div className="text-gray-500 py-10 text-center">暂无合法 Skill</div>
            ) : (
              skills.map((skill) => (
                <button
                  key={`${skill.scope}:${skill.package_path}`}
                  onClick={() => void selectSkill(skill)}
                  className={`w-full text-left p-4 rounded-xl border transition ${
                    selected?.scope === skill.scope && selected.package_path === skill.package_path
                      ? 'border-gray-900 bg-gray-100 dark:bg-zinc-800'
                      : 'border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <Folder size={18} className="mt-0.5 text-amber-600 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">{skill.name}</span>
                        <span className="text-[11px] text-gray-500">{skill.scope}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{skill.description || skill.error}</p>
                      {skill.package_status === 'invalid' && (
                        <span className="inline-flex items-center gap-1 text-xs text-red-600 mt-2">
                          <AlertCircle size={13} />
                          {skill.error || '包不可用'}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>

          <div className="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-xl overflow-hidden">
            {!selected ? (
              <div className="h-full flex items-center justify-center text-gray-500">选择一个 Skill 查看文件</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-[240px_1fr] h-full">
                <div className="border-b md:border-b-0 md:border-r border-gray-200 dark:border-zinc-700 p-4 overflow-y-auto">
                  <div className="font-medium truncate">{selected.name}</div>
                  <div className="text-xs text-gray-500 mt-1 break-all">{selected.mount_path}</div>
                  <div className="mt-4 space-y-1">
                    {treeLoading ? (
                      <div className="text-sm text-gray-500">读取文件树...</div>
                    ) : groupedTree.map(([group, nodes]) => (
                      <div key={group}>
                        <div className="text-xs font-medium text-gray-500 mb-1">{group}</div>
                        {nodes.map((node) => (
                          <button
                            key={node.path}
                            onClick={() => void openFile(node)}
                            className="w-full text-left flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 text-sm"
                          >
                            <FileText size={14} className="shrink-0" />
                            <span className="truncate">{node.path}</span>
                          </button>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
                <pre className="p-5 overflow-auto text-sm leading-6 whitespace-pre-wrap font-mono">
                  {preview?.content ?? '选择文件查看内容'}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SkillsPage
