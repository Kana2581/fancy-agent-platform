import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { Edit2, Loader2, MessageCirclePlus, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAppContext } from '../context/AppContext'
import Modal from '../components/Modal'
import LLMForm from '../components/LLMForm'
import { AgentsService, LlmModelsService, SessionsService } from '../api'
import type { LLMOut } from '../api'

const LLMSettingsPage: React.FC = () => {
  const navigate = useNavigate()
  const { llmModels, setLLMModels, setAgents, refreshSessions, refreshLLMs, setSelectedSession } =
    useAppContext()

  useEffect(() => {
    void refreshLLMs()
  }, [refreshLLMs])

  const [showLLMModal, setShowLLMModal] = useState(false)
  const [editingLLMItem, setEditingLLMItem] = useState<(typeof llmModels)[0] | null>(null)
  const [savingAction, setSavingAction] = useState<'save' | 'start' | null>(null)
  const [quickStartingModelId, setQuickStartingModelId] = useState<number | null>(null)
  const [llmForm, setLLMForm] = useState({
    provider: 'OpenAI',
    model_name: '',
    base_url: '',
    api_key: '',
  })

  const openLLMModal = (llm: (typeof llmModels)[0] | null = null) => {
    if (llm) {
      setEditingLLMItem(llm)
      setLLMForm({
        provider: llm.provider,
        model_name: llm.model_name,
        base_url: llm.base_url || '',
        api_key: '',
      })
    } else {
      setEditingLLMItem(null)
      setLLMForm({ provider: 'OpenAI', model_name: '', base_url: '', api_key: '' })
    }
    setShowLLMModal(true)
  }

  const createAgentAndStartChat = async (llm: LLMOut, trackModelButton = false) => {
    if (trackModelButton) {
      setQuickStartingModelId(llm.id)
    }

    let agentDescription = `${llm.provider} ${llm.model_name} 助手`
    try {
      const agent = await AgentsService.createAgentApiV1AgentsPost({
        avatar: '🤖',
        description: agentDescription,
        model_id: llm.id,
        system_prompt: '你是一个有帮助的 AI 助手。',
        max_token_size: 4096,
        human_in_the_loop: false,
        mcp_ids: [],
      })
      agentDescription = agent.description || agentDescription
      setAgents((prev) => (prev.some((item) => item.id === agent.id) ? prev : [...prev, agent]))

      try {
        const session = await SessionsService.createSessionApiV1SessionsPost({
          agent_id: agent.id,
          title: `与${agentDescription}的新会话`,
          is_active: true,
        })
        refreshSessions()
        setSelectedSession(session.id)
        void navigate(`/chat/${session.id}`)
        return true
      } catch (error) {
        console.error('创建会话失败:', error)
        toast.error('会话创建失败，请在 Agents 页面开始对话')
        return false
      }
    } catch (error) {
      console.error('创建 Agent 失败:', error)
      toast.error('Agent 创建失败，请稍后在 Agents 页面手动创建')
      return false
    } finally {
      if (trackModelButton) {
        setQuickStartingModelId(null)
      }
    }
  }

  const saveLLM = async (startChat = false) => {
    setSavingAction(startChat ? 'start' : 'save')
    try {
      let saved: LLMOut
      if (editingLLMItem) {
        saved = await LlmModelsService.updateLlmApiV1LlmLlmIdPut(editingLLMItem.id, llmForm)
        setLLMModels((prev) => prev.map((l) => (l.id === saved.id ? saved : l)))
      } else {
        saved = await LlmModelsService.createLlmApiV1LlmPost(llmForm)
        setLLMModels((prev) => [...prev, saved])
      }

      setShowLLMModal(false)
      if (startChat) {
        await createAgentAndStartChat(saved)
      }
    } catch (error) {
      console.error('保存模型失败:', error)
      toast.error('保存模型失败')
    } finally {
      setSavingAction(null)
    }
  }

  const deleteLLM = async (id: number) => {
    if (!confirm('确定要删除这个 LLM 模型吗？')) return
    await LlmModelsService.deleteLlmApiV1LlmLlmIdDelete(id)
    setLLMModels(llmModels.filter((l) => l.id !== id))
  }

  return (
    <div className="p-8 overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold mb-8 text-gray-800">模型设置</h2>

        <div className="bg-white dark:bg-zinc-900 rounded-xl p-8 border border-gray-200 dark:border-zinc-700">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold text-gray-800">LLM 模型</h3>
            <button
              onClick={() => openLLMModal()}
              className="px-4 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm rounded-xl hover:opacity-90 transition-all font-medium"
            >
              添加模型
            </button>
          </div>
          <div className="space-y-3">
            {llmModels.map((model) => (
              <div
                key={model.id}
                className="flex items-center justify-between p-5 bg-white dark:bg-zinc-900 rounded-2xl group hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all border border-gray-200 dark:border-zinc-800"
              >
                <div>
                  <div className="font-semibold text-gray-800">{model.model_name}</div>
                  <div className="text-sm text-gray-600 mt-1">{model.provider}</div>
                </div>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => createAgentAndStartChat(model, true)}
                    disabled={quickStartingModelId !== null}
                    className="p-2.5 hover:bg-gray-100 dark:hover:bg-zinc-700 text-gray-700 dark:text-zinc-300 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    title="用此模型创建 Agent 并开始聊天"
                  >
                    {quickStartingModelId === model.id ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <MessageCirclePlus size={18} />
                    )}
                  </button>
                  <button
                    onClick={() => openLLMModal(model)}
                    className="p-2.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-xl transition-all"
                  >
                    <Edit2 size={18} className="text-gray-700" />
                  </button>
                  <button
                    onClick={() => deleteLLM(model.id)}
                    className="p-2.5 hover:bg-red-100 text-red-600 rounded-xl transition-all"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Modal
        show={showLLMModal}
        onClose={() => setShowLLMModal(false)}
        title={editingLLMItem ? '编辑 LLM 模型' : '添加 LLM 模型'}
      >
        <LLMForm
          form={llmForm}
          onChange={setLLMForm}
          onSave={() => saveLLM(false)}
          onSaveAndStart={editingLLMItem ? undefined : () => saveLLM(true)}
          onCancel={() => setShowLLMModal(false)}
          editingId={editingLLMItem?.id ?? null}
          savingAction={savingAction}
        />
      </Modal>
    </div>
  )
}

export default LLMSettingsPage
