import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bot,
  Brain,
  FileText,
  Zap,
  Globe,
  Image,
  Wrench,
  ShieldCheck,
  Hash,
  MessageSquare,
  Users,
  Cpu,
  Plug,
  Clock,
  BarChart2,
  GalleryHorizontalEnd,
  ImageIcon,
  Palette,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Database,
  Lightbulb,
  Network,
  Search,
  AlertCircle,
} from 'lucide-react'
import { HelpDocsService } from '../api'
import type { HelpDocumentOut } from '../api'
import type { HelpDocumentSummaryOut } from '../api'

const groupColors: Record<string, string> = {
  对话区: 'bg-gray-100 dark:bg-zinc-800 border-gray-200 dark:border-zinc-700',
  配置区: 'bg-gray-100 dark:bg-zinc-800 border-gray-200 dark:border-zinc-700',
  知识增强: 'from-amber-400/20 to-orange-400/20 border-amber-300/30',
  扩展功能: 'from-emerald-400/20 to-teal-400/20 border-emerald-300/30',
}

const groupOrder = ['对话区', '配置区', '知识增强', '扩展功能']

const iconMap: Record<string, React.ReactNode> = {
  bot: <Bot size={20} />,
  brain: <Brain size={20} />,
  'file-text': <FileText size={20} />,
  zap: <Zap size={20} />,
  globe: <Globe size={20} />,
  image: <Image size={20} />,
  wrench: <Wrench size={20} />,
  'shield-check': <ShieldCheck size={20} />,
  hash: <Hash size={20} />,
  'message-square': <MessageSquare size={16} />,
  users: <Users size={16} />,
  cpu: <Cpu size={16} />,
  plug: <Plug size={20} />,
  clock: <Clock size={16} />,
  'bar-chart-2': <BarChart2 size={16} />,
  'gallery-horizontal-end': <GalleryHorizontalEnd size={16} />,
  'image-icon': <ImageIcon size={16} />,
  palette: <Palette size={20} />,
  database: <Database size={20} />,
  lightbulb: <Lightbulb size={20} />,
  network: <Network size={20} />,
}

const renderIcon = (iconKey?: string | null, size: 'sm' | 'md' = 'md') => {
  const icon = iconKey ? iconMap[iconKey] : null
  if (icon) return icon
  return size === 'sm' ? <FileText size={16} /> : <FileText size={20} />
}

const HelpPage: React.FC = () => {
  const navigate = useNavigate()
  const [docs, setDocs] = useState<HelpDocumentSummaryOut[]>([])
  const [selectedDoc, setSelectedDoc] = useState<HelpDocumentOut | null>(null)
  const [expandedGroup, setExpandedGroup] = useState<number | null>(0)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const loadDocs = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await HelpDocsService.listHelpDocuments(0, 200)
        if (!cancelled) {
          setDocs(data)
        }
      } catch (err) {
        console.error('加载帮助文档失败:', err)
        if (!cancelled) {
          setError('帮助文档加载失败，请确认后端服务已启动且文档已导入。')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadDocs()
    return () => {
      cancelled = true
    }
  }, [])

  const filteredDocs = useMemo(() => {
    const keyword = query.trim().toLowerCase()
    if (!keyword) return docs
    return docs.filter(
      (doc) =>
        doc.title.toLowerCase().includes(keyword) ||
        doc.summary.toLowerCase().includes(keyword) ||
        (doc.category ?? '').toLowerCase().includes(keyword)
    )
  }, [docs, query])

  const overview = filteredDocs.find((doc) => doc.doc_type === 'overview')
  const agentComponents = filteredDocs.filter((doc) => doc.doc_type === 'agent_component')
  const knowledgeFeatures = filteredDocs.filter((doc) => doc.doc_type === 'knowledge_feature')
  const pageDocs = filteredDocs.filter((doc) => doc.doc_type === 'page')

  const pageGroups = groupOrder
    .map((category) => ({
      label: category,
      color: groupColors[category],
      pages: pageDocs.filter((doc) => doc.category === category),
    }))
    .filter((group) => group.pages.length > 0)

  const loadDetail = async (slug: string) => {
    try {
      setDetailLoading(true)
      const doc = await HelpDocsService.getHelpDocument(slug)
      setSelectedDoc(doc)
    } catch (err) {
      console.error('加载帮助文档详情失败:', err)
      setError('帮助文档详情加载失败。')
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-8">
      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg- flex items-center justify-center shadow-lg">
              <Bot size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">{overview?.title ?? '使用帮助'}</h1>
              <p className="text-sm text-gray-600 mt-0.5">
                {overview?.summary ?? '了解平台各功能模块，快速上手 Fancy Agent'}
              </p>
            </div>
          </div>
          <div className="relative w-full lg:w-80">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索帮助文档"
              className="w-full pl-9 pr-4 py-2.5 bg-gray-100 dark:bg-zinc-700 border border-gray-200 dark:border-zinc-700 rounded-2xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none text-sm text-gray-800 placeholder-gray-500"
            />
          </div>
        </div>
        {overview && (
          <div className="text-gray-700 text-sm leading-relaxed mt-5 whitespace-pre-line">
            {overview.summary}
          </div>
        )}
        <div className="mt-5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-2xl p-4">
          <p className="text-xs font-semibold text-gray-700 dark:text-zinc-300 mb-2">
            推荐上手流程
          </p>
          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-700">
            <span className="bg-gray-200 dark:bg-zinc-700 rounded-lg px-2.5 py-1">
              1. 添加语言模型
            </span>
            <ArrowRight size={12} className="text-gray-400" />
            <span className="bg-gray-200 dark:bg-zinc-700 rounded-lg px-2.5 py-1">
              2. 配置 MCP / API 工具（可选）
            </span>
            <ArrowRight size={12} className="text-gray-400" />
            <span className="bg-gray-200 dark:bg-zinc-700 rounded-lg px-2.5 py-1">
              3. 创建 Agent
            </span>
            <ArrowRight size={12} className="text-gray-400" />
            <span className="bg-gray-200 dark:bg-zinc-700 rounded-lg px-2.5 py-1">4. 开始对话</span>
          </div>
        </div>
      </div>

      {loading && (
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6 text-sm text-gray-600">
          正在加载帮助文档...
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 rounded-xl border border-red-300/30 p-4 flex items-center gap-3 text-sm text-red-700">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {!loading && agentComponents.length > 0 && (
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded-xl bg-gray-200 dark:bg-zinc-700 flex items-center justify-center">
              <Bot size={16} className="text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800">Agent 由哪些部分组成？</h2>
              <p className="text-xs text-gray-500 mt-0.5">每个 Agent 包含以下可配置组件</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {agentComponents.map((doc) => (
              <button
                key={doc.slug}
                type="button"
                onClick={() => loadDetail(doc.slug)}
                className="bg-white dark:bg-zinc-900 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-2xl border border-gray-200 dark:border-zinc-800 p-4 flex gap-3 text-left transition-all"
              >
                <div className="w-9 h-9 rounded-xl bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 flex items-center justify-center flex-shrink-0 text-gray-700 dark:text-zinc-300">
                  {renderIcon(doc.icon_key)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-800">{doc.title}</p>
                  <p className="text-xs text-gray-600 mt-1 leading-relaxed">{doc.summary}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {!loading && knowledgeFeatures.length > 0 && (
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded-xl bg-gray-200 dark:bg-zinc-700 /* was: from-amber-400 to-orange-500 flex items-center justify-center">
              <Brain size={16} className="text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800">知识增强能力</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                让 Agent 拥有长期记忆、可复用技能与结构化知识
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {knowledgeFeatures.map((doc) => (
              <button
                key={doc.slug}
                type="button"
                onClick={() => loadDetail(doc.slug)}
                className="bg-gray-200 dark:bg-zinc-700 /* was: from-amber-400/15 to-yellow-400/15 hover:from-amber-400/25 hover:to-yellow-400/25 border border-amber-300/30 rounded-2xl p-5 text-left transition-all"
              >
                <div className="flex items-center gap-2.5 mb-3">
                  <div className="w-9 h-9 rounded-xl bg-gray-200 dark:bg-zinc-700 /* was: from-amber-400/40 to-yellow-400/40 border border-amber-300/40 flex items-center justify-center text-amber-700">
                    {renderIcon(doc.icon_key)}
                  </div>
                  <p className="text-sm font-bold text-gray-800">{doc.title}</p>
                </div>
                <p className="text-xs text-gray-600 leading-relaxed">{doc.summary}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {selectedDoc && (
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gray-200 dark:bg-zinc-700 flex items-center justify-center text-gray-700">
                {renderIcon(selectedDoc.icon_key)}
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-800">{selectedDoc.title}</h2>
                <p className="text-xs text-gray-500 mt-0.5">{selectedDoc.category}</p>
              </div>
            </div>
            {selectedDoc.route && (
              <button
                type="button"
                onClick={() => navigate(selectedDoc.route!)}
                className="px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-zinc-700 hover:bg-white/40 border border-gray-200 dark:border-zinc-700 text-xs text-gray-700 transition-all"
              >
                打开页面
              </button>
            )}
          </div>
          <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
            {detailLoading ? '正在加载详情...' : selectedDoc.content}
          </div>
        </div>
      )}

      {!loading && pageGroups.length > 0 && (
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded-xl bg-gray-200 dark:bg-zinc-700 /* was: from-emerald-400 to-teal-500 flex items-center justify-center">
              <Wrench size={16} className="text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-800">平台功能一览</h2>
              <p className="text-xs text-gray-500 mt-0.5">点击任意功能卡片可直接跳转</p>
            </div>
          </div>

          <div className="space-y-4">
            {pageGroups.map((group, gi) => (
              <div
                key={group.label}
                className={`bg-${group.color} rounded-2xl border overflow-hidden`}
              >
                <button
                  type="button"
                  onClick={() => setExpandedGroup(expandedGroup === gi ? null : gi)}
                  className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 dark:bg-zinc-900 transition-all"
                >
                  <span className="text-sm font-bold text-gray-800">{group.label}</span>
                  {expandedGroup === gi ? (
                    <ChevronUp size={16} className="text-gray-600" />
                  ) : (
                    <ChevronDown size={16} className="text-gray-600" />
                  )}
                </button>

                <div
                  className={`overflow-hidden transition-all duration-300 ${expandedGroup === gi ? 'max-h-[600px]' : 'max-h-0'}`}
                >
                  <div className="px-4 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {group.pages.map((doc) => (
                      <button
                        key={doc.slug}
                        type="button"
                        onClick={() => (doc.route ? navigate(doc.route) : loadDetail(doc.slug))}
                        className="bg-gray-100 dark:bg-zinc-800 hover:bg-white/35 rounded-xl border border-gray-200 dark:border-zinc-800 p-3.5 text-left flex gap-3 transition-all group"
                      >
                        <div className="w-8 h-8 rounded-lg bg-gray-200 dark:bg-zinc-700 flex items-center justify-center flex-shrink-0 text-gray-700 group-hover:scale-110 transition-transform">
                          {renderIcon(doc.icon_key, 'sm')}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <p className="text-sm font-semibold text-gray-800">{doc.title}</p>
                            {doc.route && (
                              <code className="text-xs text-gray-500 bg-gray-200 dark:bg-zinc-700 rounded px-1.5 py-0.5 font-mono">
                                {doc.route}
                              </code>
                            )}
                          </div>
                          <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                            {doc.summary}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default HelpPage
