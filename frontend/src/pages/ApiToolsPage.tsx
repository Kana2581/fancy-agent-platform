import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Copy, ArrowLeft, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { ApiToolCreate, ApiToolOut } from '../api';
import { ApiToolsService } from '../api';
import ApiToolWizard from '../components/ApiToolWizard';

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-green-400/20 text-green-800 border-green-400/30',
  POST: 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700',
  PUT: 'bg-yellow-400/20 text-yellow-800 border-yellow-400/30',
  DELETE: 'bg-red-400/20 text-red-800 border-red-400/30',
  PATCH: 'bg-purple-400/20 text-gray-700 dark:text-zinc-300 border-purple-400/30',
};

const ApiToolsPage: React.FC = () => {
  const navigate = useNavigate();
  const [tools, setTools] = useState<ApiToolOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [showWizard, setShowWizard] = useState(false);
  const [editingTool, setEditingTool] = useState<ApiToolOut | null>(null);

  const loadTools = async () => {
    try {
      const data = await ApiToolsService.listApiToolsApiV1ApiToolsGet();
      setTools(data);
    } catch (e) {
      console.error('加载 API 工具失败:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadTools(); }, []);

  const openCreate = () => {
    setEditingTool(null);
    setShowWizard(true);
  };

  const openEdit = (tool: ApiToolOut) => {
    setEditingTool(tool);
    setShowWizard(true);
  };

  const handleSave = async (data: ApiToolCreate) => {
    if (editingTool) {
      await ApiToolsService.updateApiToolApiV1ApiToolsToolIdPut(editingTool.id, data);
    } else {
      await ApiToolsService.createApiToolApiV1ApiToolsPost(data);
    }
    setShowWizard(false);
    await loadTools();
  };

  const handleDelete = async (tool: ApiToolOut) => {
    if (!confirm(`确定要删除工具「${tool.name}」吗？`)) return;
    try {
      await ApiToolsService.deleteApiToolApiV1ApiToolsToolIdDelete(tool.id);
      setTools(prev => prev.filter(t => t.id !== tool.id));
    } catch (e) {
      console.error(e);
      alert('删除失败');
    }
  };

  const handleClone = async (tool: ApiToolOut) => {
    const { id: _id, user_id: _uid, created_at: _ca, updated_at: _ua, ...rest } = tool;
    const cloned: ApiToolCreate = { ...rest, name: `${tool.name}_副本` };
    try {
      const created = await ApiToolsService.createApiToolApiV1ApiToolsPost(cloned);
      setTools(prev => [...prev, created]);
    } catch (e) {
      console.error(e);
      alert('克隆失败');
    }
  };

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
          <div>
            <h2 className="text-3xl font-bold text-gray-800">API 工具</h2>
            <p className="text-sm text-gray-600 mt-1">配置 HTTP API 工具供 Agent 调用</p>
          </div>
          <button
            onClick={openCreate}
            className="px-5 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl   transition-all flex items-center gap-2 font-medium"
          >
            <Plus size={20} />
            创建工具
          </button>
        </div>

        {/* Tool grid */}
        {loading ? (
          <div className="text-center text-gray-500 py-16">加载中...</div>
        ) : tools.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">🔧</div>
            <p className="text-gray-600 mb-2">暂无 API 工具</p>
            <p className="text-sm text-gray-500">创建工具后，可在 Agent 配置中绑定使用</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {tools.map(tool => (
              <div
                key={tool.id}
                className="bg-white dark:bg-zinc-900 rounded-xl p-6 border border-gray-200 dark:border-zinc-700 group  hover:scale-[1.02] transition-all flex flex-col"
              >
                {/* Title row */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-lg text-gray-800 truncate">{tool.name}</h3>
                    {tool.description && (
                      <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">{tool.description}</p>
                    )}
                  </div>
                  <span className={`ml-2 shrink-0 text-xs px-2.5 py-1 rounded-full border font-medium ${METHOD_COLORS[tool.method ?? ''] ?? 'bg-gray-200 text-gray-700'}`}>
                    {tool.method}
                  </span>
                </div>

                {/* URL */}
                <p className="text-xs text-gray-500 bg-black/10 rounded-xl px-3 py-2 font-mono truncate mb-3">
                  {tool.url}
                </p>

                {/* Stats */}
                <div className="flex gap-3 text-xs text-gray-600 mb-4">
                  <span className="bg-gray-100 dark:bg-zinc-800 px-2.5 py-1 rounded-full">{(tool.tool_params as unknown[])?.length ?? 0} 个参数</span>
                  <span className="bg-gray-100 dark:bg-zinc-800 px-2.5 py-1 rounded-full">{tool.param_location}</span>
                </div>

                {/* Actions */}
                <div className="mt-auto flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => openEdit(tool)}
                    className="flex-1 py-2 text-sm bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-xl transition-all flex items-center justify-center gap-1.5"
                  >
                    <Edit2 size={14} />编辑
                  </button>
                  <button
                    onClick={() => handleClone(tool)}
                    title="克隆"
                    className="p-2 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-xl transition-all"
                  >
                    <Copy size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(tool)}
                    className="p-2 hover:bg-red-100/50 text-red-500 rounded-xl transition-all"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Wizard modal */}
      {showWizard && (
        <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-50 dark:bg-zinc-900 rounded-xl w-full max-w-3xl max-h-[92vh] overflow-y-auto shadow-sm border border-gray-200 dark:border-zinc-700">
            <div className="sticky top-0 bg-gray-50 dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 px-6 py-4 flex items-center justify-between">
              <h3 className="text-xl font-semibold text-gray-800">
                {editingTool ? `编辑工具：${editingTool.name}` : '创建 API 工具'}
              </h3>
              <button
                onClick={() => setShowWizard(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded-xl transition-all text-gray-600"
              >
                <X size={18} />
              </button>
            </div>
            <div className="p-6">
              <ApiToolWizard
                initialTool={editingTool ?? undefined}
                onSave={handleSave}
                onCancel={() => setShowWizard(false)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ApiToolsPage;
