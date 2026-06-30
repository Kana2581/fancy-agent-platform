import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Zap, RefreshCw } from 'lucide-react'
import { McpService, type ToolOut, type MCPOut } from '../api'

/** 简单超时封装 */
function withTimeout<T>(promise: Promise<T>, ms = 5000): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => setTimeout(() => reject(new Error('timeout')), ms)),
  ])
}

const MCPDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [mcp, setMcp] = useState<MCPOut | null>(null)
  const [mcpLoading, setMcpLoading] = useState(true)

  const [tools, setTools] = useState<ToolOut[]>([])
  const [toolsLoading, setToolsLoading] = useState(false)
  const [toolsError, setToolsError] = useState<string | null>(null)
  const [toolsLoaded, setToolsLoaded] = useState(false)

  /** 加载 MCP 基本信息（页面一进来就拉） */
  useEffect(() => {
    if (!id) return

    setMcpLoading(true)
    McpService.getMcpApiV1McpsMcpIdGet(Number(id))
      .then(setMcp)
      .catch(() => setMcp(null))
      .finally(() => setMcpLoading(false))
  }, [id])

  /** 延迟加载 tools */
  const loadTools = async () => {
    if (!id || toolsLoading) return

    setToolsLoading(true)
    setToolsError(null)

    try {
      const data = await withTimeout(McpService.getMcpToolsApiV1McpsMcpIdToolsGet(Number(id)), 5000)
      setTools(data)
      setToolsLoaded(true)
    } catch {
      setToolsError('Tools 加载失败或超时')
    } finally {
      setToolsLoading(false)
    }
  }

  /* ---------- 页面状态 ---------- */

  if (mcpLoading) {
    return <div className="p-8 text-gray-600">加载 MCP 信息中...</div>
  }

  if (!mcp) {
    return <div className="p-8 text-red-500">MCP 不存在</div>
  }

  return (
    <div className="p-8 overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate(-1)}
            className="p-2 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-xl transition-all"
          >
            <ArrowLeft size={20} />
          </button>
          <h2 className="text-3xl font-bold text-gray-800">MCP 详情</h2>
        </div>

        {/* MCP 基本信息 */}
        <div className="bg-white dark:bg-zinc-900 rounded-xl p-8 border border-gray-200 dark:border-zinc-700 mb-8">
          <div className="flex items-center gap-4">
            <Zap size={28} className={mcp.is_enabled ? 'text-green-500' : 'text-gray-400'} />
            <div>
              <div className="text-xl font-semibold text-gray-800">{mcp.mcp_name}</div>
              <div className="text-sm text-gray-600 mt-1">Transport: {mcp.transport}</div>
            </div>
          </div>
        </div>

        {/* Tools */}
        <div className="bg-white dark:bg-zinc-900 rounded-xl p-8 border border-gray-200 dark:border-zinc-700">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold text-gray-800">Tools</h3>

            {!toolsLoaded && (
              <button
                onClick={loadTools}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 transition-all text-sm"
              >
                <RefreshCw size={16} />
                加载 Tools
              </button>
            )}
          </div>

          {/* Tools loading */}
          {toolsLoading && (
            <div className="text-sm text-gray-600">正在从 MCP Server 拉取 tools…</div>
          )}

          {/* Tools error */}
          {toolsError && (
            <div className="flex items-center justify-between text-sm text-red-500 bg-red-50/40 rounded-xl p-4">
              <span>{toolsError}</span>
              <button
                onClick={loadTools}
                className="flex items-center gap-1 text-red-600 hover:underline"
              >
                <RefreshCw size={14} />
                重试
              </button>
            </div>
          )}

          {/* Tools list */}
          {!toolsLoading && toolsLoaded && tools.length > 0 && (
            <div className="space-y-4">
              {tools.map((tool, index) => (
                <div
                  key={index}
                  className="p-6 bg-gray-50 dark:bg-zinc-800 rounded-xl border border-gray-200 dark:border-zinc-700 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all"
                >
                  <div className="font-semibold text-gray-800 text-lg">{tool.name}</div>

                  <div className="text-sm text-gray-600 mt-2">{tool.description}</div>

                  <div className="mt-4">
                    <div className="text-sm font-medium text-gray-700 mb-2">Parameters</div>
                    <pre className="text-xs bg-black/5 rounded-xl p-4 overflow-x-auto">
                      {JSON.stringify(tool.parameters, null, 2)}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Empty */}
          {!toolsLoading && toolsLoaded && tools.length === 0 && (
            <div className="text-sm text-gray-500">当前 MCP 没有暴露任何工具</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default MCPDetailPage
