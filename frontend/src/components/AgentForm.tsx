import React, { useState } from 'react'
import { Save, ChevronDown, ChevronUp } from 'lucide-react'
import type { ApiToolOut } from '../api/models/ApiToolOut'
import type { ImageToolOut } from '../api/models/ImageToolOut'
import type { BuiltinToolInfo } from '../api/models/BuiltinToolInfo'
import type { PromptTemplateOut } from '../api/models/PromptTemplateOut'
import ThemedSelect from './ThemedSelect'

interface AgentFormData {
  avatar: string
  description: string
  model_id: number
  system_prompt: string
  max_token_size: number
  human_in_the_loop: boolean
  mcp_ids: number[]
  api_tool_ids: number[]
  image_tool_ids: number[]
  builtin_tool_types: string[]
}

interface AgentMCP {
  id: number
  mcp_name: string
  is_enabled: boolean
  has_mcp: boolean
}

interface AgentFormProps {
  form: AgentFormData
  onChange: (form: AgentFormData) => void
  onSave: () => void
  onCancel: () => void
  llmModels: Array<{ id: number; provider: string; model_name: string }>
  availableMcps: AgentMCP[]
  availableApiTools: ApiToolOut[]
  availableImageTools: ImageToolOut[]
  availableBuiltinTools: BuiltinToolInfo[]
  promptTemplates: PromptTemplateOut[]
}

const emojiList = ['🤖', '💼', '📝', '🎨', '🔬', '⚡', '🎯', '🚀', '💡', '🎭', '🎪', '🎸']

const AgentForm: React.FC<AgentFormProps> = ({
  form,
  onChange,
  onSave,
  onCancel,
  llmModels,
  availableMcps,
  availableApiTools,
  availableImageTools,
  availableBuiltinTools,
  promptTemplates,
}) => {
  const [showTemplates, setShowTemplates] = useState(false)

  const injectTemplate = (template: PromptTemplateOut) => {
    const sep = form.system_prompt ? '\n\n' : ''
    onChange({ ...form, system_prompt: form.system_prompt + sep + template.content })
    setShowTemplates(false)
  }

  const toggleMcp = (mcpId: number) => {
    if (form.mcp_ids.includes(mcpId)) {
      onChange({ ...form, mcp_ids: form.mcp_ids.filter((id) => id !== mcpId) })
    } else {
      onChange({ ...form, mcp_ids: [...form.mcp_ids, mcpId] })
    }
  }

  const toggleApiTool = (toolId: number) => {
    if (form.api_tool_ids.includes(toolId)) {
      onChange({ ...form, api_tool_ids: form.api_tool_ids.filter((id) => id !== toolId) })
    } else {
      onChange({ ...form, api_tool_ids: [...form.api_tool_ids, toolId] })
    }
  }

  const toggleImageTool = (toolId: number) => {
    if (form.image_tool_ids.includes(toolId)) {
      onChange({ ...form, image_tool_ids: form.image_tool_ids.filter((id) => id !== toolId) })
    } else {
      onChange({ ...form, image_tool_ids: [...form.image_tool_ids, toolId] })
    }
  }

  const toggleBuiltinTool = (toolType: string) => {
    if (form.builtin_tool_types.includes(toolType)) {
      onChange({
        ...form,
        builtin_tool_types: form.builtin_tool_types.filter((t) => t !== toolType),
      })
    } else {
      onChange({ ...form, builtin_tool_types: [...form.builtin_tool_types, toolType] })
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-800 mb-3">选择头像</label>
        <div className="grid grid-cols-6 gap-2">
          {emojiList.map((emoji) => (
            <button
              key={emoji}
              onClick={() => onChange({ ...form, avatar: emoji })}
              className={`text-3xl p-3 rounded-2xl border-2 transition-all ${
                form.avatar === emoji
                  ? 'border-cyan-400 bg-gray-200 dark:bg-zinc-700 shadow-lg scale-105'
                  : 'border-gray-200 dark:border-zinc-700 bg-gray-50 dark:bg-zinc-900 hover:border-white/50 hover:bg-gray-100 dark:hover:bg-zinc-700'
              }`}
            >
              {emoji}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">描述 *</label>
        <input
          type="text"
          value={form.description}
          onChange={(e) => onChange({ ...form, description: e.target.value })}
          placeholder="例如：代码助手"
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none transition-all text-gray-800 placeholder-gray-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">LLM 模型 *</label>
        <ThemedSelect
          value={form.model_id}
          onChange={(v) => onChange({ ...form, model_id: parseInt(v) })}
          options={llmModels.map((model) => ({
            value: model.id,
            label: `${model.provider} - ${model.model_name}`,
          }))}
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none transition-all text-gray-800 dark:text-white"
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-sm font-medium text-gray-800">系统提示词 *</label>
          {promptTemplates.length > 0 && (
            <button
              type="button"
              onClick={() => setShowTemplates((v) => !v)}
              className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:shadow-md  font-medium transition-all"
            >
              从模板插入
              {showTemplates ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          )}
        </div>
        {showTemplates && (
          <div className="mb-2 max-h-48 overflow-y-auto space-y-1 p-2 bg-gray-50 dark:bg-zinc-900 border border-gray-200 dark:border-zinc-700 rounded-2xl">
            {promptTemplates.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => injectTemplate(t)}
                className="w-full text-left px-3 py-2 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-600 transition-all"
              >
                <span className="text-sm font-medium text-gray-800">{t.name}</span>
                {t.category && (
                  <span className="ml-2 text-xs text-gray-500 bg-gray-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full">
                    {t.category}
                  </span>
                )}
                {t.description && (
                  <p className="text-xs text-gray-500 mt-0.5 truncate">{t.description}</p>
                )}
              </button>
            ))}
          </div>
        )}
        <textarea
          value={form.system_prompt}
          onChange={(e) => onChange({ ...form, system_prompt: e.target.value })}
          placeholder="定义 Agent 的角色和行为..."
          rows={5}
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none resize-none transition-all text-gray-800 placeholder-gray-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">上下文 Token 上限</label>
        <input
          type="number"
          value={form.max_token_size}
          onChange={(e) => onChange({ ...form, max_token_size: parseInt(e.target.value) })}
          min="1"
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none transition-all text-gray-800"
        />
        <p className="text-xs text-gray-600 mt-2">历史消息超过此 Token 数时自动压缩上下文</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">工具审批</label>
        <label className="flex items-center gap-3 p-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-600 transition-all cursor-pointer">
          <input
            type="checkbox"
            checked={form.human_in_the_loop}
            onChange={(e) => onChange({ ...form, human_in_the_loop: e.target.checked })}
            className="w-5 h-5 rounded border-gray-300 text-gray-600 dark:text-zinc-300 focus:ring-gray-400 dark:focus:ring-zinc-500 focus:ring-2"
          />
          <div>
            <span className="text-sm text-gray-800 font-medium">开启 Human-in-the-loop</span>
            <p className="text-xs text-gray-500 mt-0.5">
              每次工具调用前暂停，等待人工审批后再继续执行
            </p>
          </div>
        </label>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-3">MCP 工具</label>
        {availableMcps.length === 0 ? (
          <p className="text-sm text-gray-500 italic">暂无可用的 MCP 工具</p>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {availableMcps
              .filter((mcp) => mcp.is_enabled)
              .map((mcp) => (
                <label
                  key={mcp.id}
                  className="flex items-center gap-3 p-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-600 transition-all cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={form.mcp_ids.includes(mcp.id)}
                    onChange={() => toggleMcp(mcp.id)}
                    className="w-5 h-5 rounded border-gray-300 text-gray-600 dark:text-zinc-300 focus:ring-gray-400 dark:focus:ring-zinc-500 focus:ring-2"
                  />
                  <span className="text-sm text-gray-800 font-medium">{mcp.mcp_name}</span>
                </label>
              ))}
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-3">HTTP API 工具</label>
        {availableApiTools.length === 0 ? (
          <p className="text-sm text-gray-500 italic">暂无可用的 API 工具</p>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {availableApiTools.map((tool) => (
              <label
                key={tool.id}
                className="flex items-center gap-3 p-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-600 transition-all cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={form.api_tool_ids.includes(tool.id)}
                  onChange={() => toggleApiTool(tool.id)}
                  className="w-5 h-5 rounded border-gray-300 text-gray-600 dark:text-zinc-300 focus:ring-gray-400 dark:focus:ring-zinc-500 focus:ring-2"
                />
                <div className="flex-1 min-w-0">
                  <span className="text-sm text-gray-800 font-medium">{tool.name}</span>
                  {tool.description && (
                    <span className="text-xs text-gray-500 ml-2 truncate">{tool.description}</span>
                  )}
                </div>
                <span className="text-xs text-gray-500 bg-gray-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full shrink-0">
                  {tool.method}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-3">图像生成工具</label>
        {availableImageTools.length === 0 ? (
          <p className="text-sm text-gray-500 italic">暂无可用的图像生成工具</p>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {availableImageTools.map((tool) => (
              <label
                key={tool.id}
                className="flex items-center gap-3 p-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-600 transition-all cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={form.image_tool_ids.includes(tool.id)}
                  onChange={() => toggleImageTool(tool.id)}
                  className="w-5 h-5 rounded border-gray-300 text-gray-600 dark:text-zinc-300 focus:ring-gray-400 dark:focus:ring-zinc-500 focus:ring-2"
                />
                <div className="flex-1 min-w-0">
                  <span className="text-sm text-gray-800 font-medium">{tool.name}</span>
                  {tool.description && (
                    <span className="text-xs text-gray-500 ml-2 truncate">{tool.description}</span>
                  )}
                </div>
                <span className="text-xs text-gray-500 bg-gray-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full shrink-0">
                  {tool.provider}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-3">内置工具</label>
        {availableBuiltinTools.length === 0 ? (
          <p className="text-sm text-gray-500 italic">暂无可用的内置工具</p>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {availableBuiltinTools.map((tool) => (
              <label
                key={tool.tool_type}
                className="flex items-center gap-3 p-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl hover:bg-gray-200 dark:hover:bg-zinc-600 transition-all cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={form.builtin_tool_types.includes(tool.tool_type)}
                  onChange={() => toggleBuiltinTool(tool.tool_type)}
                  className="w-5 h-5 rounded border-gray-300 text-gray-600 dark:text-zinc-300 focus:ring-gray-400 dark:focus:ring-zinc-500 focus:ring-2"
                />
                <div className="flex-1 min-w-0">
                  <span className="text-sm text-gray-800 font-medium block truncate">
                    {tool.name}
                  </span>
                  {tool.description && (
                    <span className="text-xs text-gray-500 block truncate mt-0.5">
                      {tool.description}
                    </span>
                  )}
                </div>
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="flex gap-3 pt-4">
        <button
          onClick={onSave}
          className="flex-1 px-4 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:opacity-90 transition-all flex items-center justify-center gap-2 font-medium"
        >
          <Save size={18} />
          保存
        </button>
        <button
          onClick={onCancel}
          className="px-6 py-3 bg-gray-200 dark:bg-zinc-700 text-gray-700 rounded-2xl hover:bg-white/40 transition-all"
        >
          取消
        </button>
      </div>
    </div>
  )
}

export default AgentForm
