import React, { useState, useEffect } from 'react'
import { Mail, Save, Trash2, ToggleLeft, ToggleRight } from 'lucide-react'
import ThemedSelect from './ThemedSelect'
import { useAppContext } from '../context/AppContext'
import { EmailAgentService } from '../api/services/EmailAgentService'
import type { UserEmailAgentOut } from '../api/models/UserEmailAgentOut'

const EmailAgentConfig: React.FC = () => {
  const { agents } = useAppContext()
  const [config, setConfig] = useState<UserEmailAgentOut | null>(null)
  const [selectedAgentId, setSelectedAgentId] = useState<number>(0)
  const [isEnabled, setIsEnabled] = useState(true)
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(true)

  useEffect(() => {
    void loadConfig()
  }, [])

  const loadConfig = async () => {
    setFetching(true)
    try {
      const data = await EmailAgentService.getEmailAgentApiV1EmailAgentGet()
      setConfig(data)
      setSelectedAgentId(data.agent_id)
      setIsEnabled(data.is_enabled)
    } catch {
      setConfig(null)
    } finally {
      setFetching(false)
    }
  }

  const handleSave = async () => {
    if (!selectedAgentId) {
      alert('请选择一个 Agent')
      return
    }
    setLoading(true)
    try {
      if (config) {
        const updated = await EmailAgentService.updateEmailAgentApiV1EmailAgentPut({
          agent_id: selectedAgentId,
          is_enabled: isEnabled,
        })
        setConfig(updated)
      } else {
        const created = await EmailAgentService.createEmailAgentApiV1EmailAgentPost({
          agent_id: selectedAgentId,
        })
        setConfig(created)
        setIsEnabled(created.is_enabled)
      }
    } catch (e) {
      console.error(e)
      alert('保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('确定要删除邮件 Agent 配置吗？')) return
    setLoading(true)
    try {
      await EmailAgentService.deleteEmailAgentApiV1EmailAgentDelete()
      setConfig(null)
      setSelectedAgentId(0)
      setIsEnabled(true)
    } catch (e) {
      console.error(e)
      alert('删除失败')
    } finally {
      setLoading(false)
    }
  }

  if (fetching) {
    return (
      <div className="bg-white dark:bg-zinc-900 rounded-xl p-6 border border-gray-200 dark:border-zinc-700">
        <div className="flex items-center gap-3 mb-4">
          <Mail size={20} className="text-blue-500" />
          <h3 className="font-semibold text-gray-800 text-lg">邮件 Agent 配置</h3>
        </div>
        <p className="text-gray-500 text-sm">加载中...</p>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl p-6 border border-gray-200 dark:border-zinc-700">
      <div className="flex items-center gap-3 mb-4">
        <Mail size={20} className="text-blue-500" />
        <h3 className="font-semibold text-gray-800 text-lg">邮件 Agent 配置</h3>
      </div>

      <p className="text-sm text-gray-600 mb-5">
        配置后，向服务邮箱发送邮件即可与 AI 对话。AI 将自动回复到您的邮箱。
      </p>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">选择 Agent</label>
          <ThemedSelect
            value={selectedAgentId}
            onChange={(v) => setSelectedAgentId(Number(v))}
            placeholder="请选择 Agent"
            options={agents.map((agent) => ({
              value: agent.id,
              label: `${agent.avatar} ${agent.description}`,
            }))}
            className="w-full px-3 py-2 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl text-gray-800 focus:outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600"
          />
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">启用邮件对话</span>
          <button onClick={() => setIsEnabled(!isEnabled)} className="focus:outline-none">
            {isEnabled ? (
              <ToggleRight size={28} className="text-blue-500" />
            ) : (
              <ToggleLeft size={28} className="text-gray-400" />
            )}
          </button>
        </div>

        {config && (
          <div className="text-xs text-gray-500 bg-gray-100 dark:bg-zinc-800 rounded-xl px-3 py-2">
            当前绑定 Session: {config.session_id || '首次收信时自动创建'}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={loading || !selectedAgentId}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-xl hover:shadow-lg transition-all disabled:opacity-50 font-medium text-sm"
          >
            <Save size={16} />
            {config ? '更新配置' : '保存配置'}
          </button>
          {config && (
            <button
              onClick={handleDelete}
              disabled={loading}
              className="flex items-center justify-center gap-2 px-4 py-2.5 bg-red-100 text-red-600 rounded-xl hover:bg-red-200 transition-all disabled:opacity-50 text-sm"
            >
              <Trash2 size={16} />
              删除
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default EmailAgentConfig
