import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAppContext } from '../context/AppContext';
import Modal from '../components/Modal';
import AgentForm from '../components/AgentForm';
import EmailAgentConfig from '../components/EmailAgentConfig';
import { AgentsService, SessionsService, McpService } from '../api';
import type { AgentOut, AgentFullOut, AgentMCPOut } from '../api';
import { ApiToolsService, AgentApiToolsService, AgentImageToolsService, ImageToolsService } from '../api';
import { AgentBuiltinToolsService, BuiltinToolsService, PromptTemplatesService } from '../api';
import type { ApiToolOut, ImageToolOut, BuiltinToolInfo, PromptTemplateOut } from '../api';

const AgentsPage: React.FC = () => {
  const navigate = useNavigate();
  const { llmModels, setSelectedSession, refreshSessions } = useAppContext();

  const [agents, setAgents] = useState<AgentOut[]>([]);
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [editingItem, setEditingItem] = useState<AgentFullOut | null>(null);

  const [availableMcps, setAvailableMcps] = useState<AgentMCPOut[]>([]);
  const [availableApiTools, setAvailableApiTools] = useState<ApiToolOut[]>([]);
  const [availableImageTools, setAvailableImageTools] = useState<ImageToolOut[]>([]);
  const [availableBuiltinTools, setAvailableBuiltinTools] = useState<BuiltinToolInfo[]>([]);
  const [promptTemplates, setPromptTemplates] = useState<PromptTemplateOut[]>([]);

  const [agentForm, setAgentForm] = useState({
    avatar: '🤖',
    description: '',
    model_id: 1,
    system_prompt: '',
    max_token_size: 4096,
    human_in_the_loop: false,
    mcp_ids: [] as number[],
    api_tool_ids: [] as number[],
    image_tool_ids: [] as number[],
    builtin_tool_types: [] as string[],
  });

  useEffect(() => {
    loadAgents();
    ApiToolsService.listApiToolsApiV1ApiToolsGet().then(setAvailableApiTools).catch(console.error);
    ImageToolsService.listImageToolsApiV1ImageToolsGet(0, 100).then(setAvailableImageTools).catch(console.error);
    BuiltinToolsService.listAvailableBuiltinToolsApiV1BuiltinToolsGet().then(setAvailableBuiltinTools).catch(console.error);
    PromptTemplatesService.listPromptTemplates().then(setPromptTemplates).catch(console.error);
  }, []);

  const loadAgents = async () => {
    try {
      const data = await AgentsService.listAgentsApiV1AgentsGet(0, 100);
      setAgents(data);
    } finally {
      // noop
    }
  };

  const openAgentModal = async (agent: AgentOut | null = null) => {
    if (agent) {
      try {
        // 获取完整的 Agent 信息，包括 MCP 和 API 工具
        const [fullAgent, boundApiToolIds, boundImageToolIds, boundBuiltinToolTypes] = await Promise.all([
          AgentsService.getAgentApiV1AgentsAgentIdGet(agent.id),
          AgentApiToolsService.listAgentToolsApiV1AgentsAgentIdApiToolsGet(agent.id),
          AgentImageToolsService.listAgentImageToolsApiV1AgentsAgentIdImageToolsGet(agent.id),
          AgentBuiltinToolsService.listAgentBuiltinToolsApiV1AgentsAgentIdBuiltinToolsGet(agent.id),
        ]);
        setEditingItem(fullAgent);
        setAgentForm({
          avatar: fullAgent.avatar ?? '🤖',
          description: fullAgent.description ?? '',
          model_id: fullAgent.model_id,
          system_prompt: fullAgent.system_prompt ?? '',
          max_token_size: fullAgent.max_token_size ?? 4096,
          human_in_the_loop: fullAgent.human_in_the_loop ?? false,
          mcp_ids: fullAgent.mcps?.filter(mcp => mcp.has_mcp).map(mcp => mcp.id) || [],
          api_tool_ids: boundApiToolIds,
          image_tool_ids: boundImageToolIds,
          builtin_tool_types: boundBuiltinToolTypes,
        });
        // 设置可用的 MCP 列表（包含 has_mcp 状态）
        setAvailableMcps(fullAgent.mcps || []);
      } catch (error) {
        console.error('加载 Agent 详情失败:', error);
        alert('加载 Agent 详情失败');
        return;
      }
    } else {
      try {
        // 创建新 Agent 时，获取所有可用的 MCP（通过一个临时调用或者专门的接口）
        const data = await McpService.listMcpsApiV1McpsGet(0, 100);
        setAvailableMcps(data.map(mcp => ({ ...mcp, has_mcp: false })));
      } catch (error) {
        console.error('加载 MCP 列表失败:', error);
      }
      
      setEditingItem(null);
      setAgentForm({
        avatar: '🤖',
        description: '',
        model_id: llmModels?.[0]?.id ?? 0,
        system_prompt: '',
        max_token_size: 4096,
        human_in_the_loop: false,
        mcp_ids: [],
        api_tool_ids: [],
        image_tool_ids: [],
        builtin_tool_types: [],
      });
    }
    setShowAgentModal(true);
  };

  const createSession = async (agentId: number) => {
    SessionsService.createSessionApiV1SessionsPost({
      agent_id: agentId, 
      title: '新的会话呀',
      is_active: true 
    })
      .then((res) => {
        refreshSessions();
        navigate(`/chat/${res.id}`);
        setSelectedSession(res.id);
      })
      .catch((error) => {
        console.error('创建会话失败:', error);
        alert('创建会话失败，请重试。');
      });
  };

  const saveAgent = async () => {
    try {
      const { api_tool_ids, image_tool_ids, builtin_tool_types, ...agentData } = agentForm;
      let agentId: number;

      if (editingItem) {
        await AgentsService.updateAgentApiV1AgentsAgentIdPut(editingItem.id, agentData);
        agentId = editingItem.id;
      } else {
        const created = await AgentsService.createAgentApiV1AgentsPost(agentData);
        agentId = created.id;
      }

      await Promise.all([
        AgentApiToolsService.syncAgentToolsApiV1AgentsAgentIdApiToolsPost(agentId, { tool_ids: api_tool_ids }),
        AgentImageToolsService.syncAgentImageToolsApiV1AgentsAgentIdImageToolsPost(agentId, { tool_ids: image_tool_ids }),
        AgentBuiltinToolsService.syncAgentBuiltinToolsApiV1AgentsAgentIdBuiltinToolsPost(agentId, { tool_types: builtin_tool_types }),
      ]);

      setShowAgentModal(false);
      await loadAgents();
    } catch (e) {
      console.error(e);
      alert('保存失败');
    }
  };

  const deleteAgent = async (id: number) => {
    if (!confirm('确定要删除这个 Agent 吗？')) return;

    try {
      await AgentsService.deleteAgentApiV1AgentsAgentIdDelete(id);
      setAgents(prev => prev.filter(a => a.id !== id));
    } catch (e) {
      console.error(e);
      alert('删除失败');
    }
  };

  return (
    <div className="p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 px-3 py-2 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-50 dark:bg-zinc-800/300 rounded-xl transition"
          >
            <ArrowLeft size={16} />
            返回
          </button>
          <h2 className="text-3xl font-bold text-gray-800">我的 Agents</h2>
          <button 
            onClick={() => openAgentModal()}
            className="px-5 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl   transition-all flex items-center gap-2 font-medium"
          >
            <Plus size={20} />
            创建 Agent
          </button>
        </div>
        
        <div className="mb-8">
          <EmailAgentConfig />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map(agent => (
            <div
              key={agent.id}
              className="bg-white dark:bg-zinc-900 rounded-xl p-7 shadow-lg  transition-all border border-gray-200 dark:border-zinc-700 group "
            >
              <div className="text-5xl mb-4">{agent.avatar}</div>
              <h3 className="font-semibold text-xl mb-3 text-gray-800">{agent.description}</h3>
              <p className="text-sm text-gray-600 mb-5 line-clamp-2">{agent.system_prompt}</p>
              <div className="flex items-center justify-between text-xs text-gray-600 mb-4">
                <span className="px-3 py-1.5 bg-gray-100 dark:bg-zinc-800 rounded-full">上下文 Token 上限: {agent.max_token_size ?? 0}</span>
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      openAgentModal(agent);
                    }}
                    className="p-2 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-xl transition-all"
                  >
                    <Edit2 size={16} className="text-gray-700" />
                  </button>
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteAgent(agent.id);
                    }}
                    className="p-2 hover:bg-red-100 text-red-600 rounded-xl transition-all"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <button
                onClick={() => {
                  createSession(agent.id);
                }}
                className="w-full px-4 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm rounded-2xl hover:shadow-lg transition-all font-medium"
              >
                开始对话
              </button>
            </div>
          ))}
        </div>
      </div>

      <Modal 
        show={showAgentModal} 
        onClose={() => setShowAgentModal(false)} 
        title={editingItem ? '编辑 Agent' : '创建 Agent'}
      >
        <AgentForm
          form={agentForm}
          onChange={setAgentForm}
          onSave={saveAgent}
          onCancel={() => setShowAgentModal(false)}
          llmModels={llmModels}
          availableMcps={availableMcps}
          availableApiTools={availableApiTools}
          availableImageTools={availableImageTools}
          availableBuiltinTools={availableBuiltinTools}
          promptTemplates={promptTemplates}
        />
      </Modal>
    </div>
  );
};

export default AgentsPage;