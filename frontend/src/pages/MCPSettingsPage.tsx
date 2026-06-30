import React, { useEffect, useState } from 'react'
import { Edit2, Trash2, Zap, Eye } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAppContext } from '../context/AppContext'
import Modal from '../components/Modal'
import MCPForm from '../components/MCPForm'
import { McpService } from '../api'

const MCPSettingsPage: React.FC = () => {
  const navigate = useNavigate()
  const { mcpTools, setMCPTools, refreshMCPs } = useAppContext()

  useEffect(() => {
    void refreshMCPs()
  }, [refreshMCPs])

  const [showMCPModal, setShowMCPModal] = useState(false)
  const [editingMCPItem, setEditingMCPItem] = useState<(typeof mcpTools)[0] | null>(null)
  const [mcpForm, setMCPForm] = useState({
    mcp_name: '',
    transport: 'stdio',
    config_json: {},
    is_enabled: true,
  })

  const openMCPModal = (mcp: (typeof mcpTools)[0] | null = null) => {
    if (mcp) {
      setEditingMCPItem(mcp)
      setMCPForm({
        mcp_name: mcp.mcp_name,
        transport: mcp.transport,
        config_json: mcp.config_json || {},
        is_enabled: mcp.is_enabled,
      })
    } else {
      setEditingMCPItem(null)
      setMCPForm({ mcp_name: '', transport: 'stdio', config_json: {}, is_enabled: true })
    }
    setShowMCPModal(true)
  }

  const saveMCP = async () => {
    if (editingMCPItem) {
      const updated = await McpService.updateMcpApiV1McpsMcpIdPut(editingMCPItem.id, mcpForm)
      setMCPTools(mcpTools.map((m) => (m.id === updated.id ? updated : m)))
    } else {
      const created = await McpService.createMcpApiV1McpsPost(mcpForm)
      setMCPTools([...mcpTools, created])
    }
    setShowMCPModal(false)
  }

  const deleteMCP = async (id: number) => {
    if (!confirm('确定要删除这个 MCP 工具吗？')) return
    await McpService.deleteMcpApiV1McpsMcpIdDelete(id)
    setMCPTools(mcpTools.filter((m) => m.id !== id))
  }

  const toggleMCP = async (tool: (typeof mcpTools)[0]) => {
    const updated = await McpService.updateMcpApiV1McpsMcpIdPut(tool.id, {
      is_enabled: !tool.is_enabled,
    })
    setMCPTools(mcpTools.map((m) => (m.id === updated.id ? updated : m)))
  }

  return (
    <div className="p-8 overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold mb-8 text-gray-800">MCP 设置</h2>

        <div className="bg-white dark:bg-zinc-900 rounded-xl p-8 border border-gray-200 dark:border-zinc-700">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold text-gray-800">MCP 工具</h3>
            <button
              onClick={() => openMCPModal()}
              className="px-4 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm rounded-xl hover:opacity-90 transition-all font-medium"
            >
              添加MCP
            </button>
          </div>
          <div className="space-y-3">
            {mcpTools.map((tool) => (
              <div
                key={tool.id}
                onClick={() => navigate(`/mcp/${tool.id}`)}
                className="flex items-center justify-between p-5 bg-white dark:bg-zinc-900 rounded-2xl group hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all border border-gray-200 dark:border-zinc-800 cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <Zap size={24} className={tool.is_enabled ? 'text-green-500' : 'text-gray-400'} />
                  <div>
                    <div className="font-semibold text-gray-800">{tool.mcp_name}</div>
                    <div className="text-sm text-gray-600 mt-1">{tool.transport}</div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={tool.is_enabled}
                      onClick={(e) => e.stopPropagation()}
                      onChange={() => toggleMCP(tool)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gray-900 dark:peer-checked:bg-white"></div>
                  </label>
                  <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        void navigate(`/mcp/${tool.id}`)
                      }}
                      className="p-2.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-xl transition-all"
                      title="查看详情"
                    >
                      <Eye size={18} className="text-gray-700" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        openMCPModal(tool)
                      }}
                      className="p-2.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-xl transition-all"
                    >
                      <Edit2 size={18} className="text-gray-700" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        void deleteMCP(tool.id)
                      }}
                      className="p-2.5 hover:bg-red-100 text-red-600 rounded-xl transition-all"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Modal
        show={showMCPModal}
        onClose={() => setShowMCPModal(false)}
        title={editingMCPItem ? '编辑 MCP 工具' : '添加 MCP 工具'}
      >
        <MCPForm
          key={editingMCPItem?.id ?? 'new'}
          form={mcpForm}
          onChange={setMCPForm}
          onSave={saveMCP}
          onCancel={() => setShowMCPModal(false)}
        />
      </Modal>
    </div>
  )
}

export default MCPSettingsPage
