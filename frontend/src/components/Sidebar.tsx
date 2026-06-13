import React, { useState, useEffect, useCallback } from 'react';
import { Moon, Sun, Trash2, ChevronLeft, ChevronRight, Edit2, Check, X, Search, ChevronUp, ChevronDown, Clock, Wrench, ImageIcon, MessageCircle, GalleryHorizontalEnd, BarChart2, LogOut, Cpu, Plug, FileText, HelpCircle, Zap, Brain, Network, Webhook, Eye } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { SessionOut } from '../api';
import { SessionsService } from '../api';
import { useAppContext } from '../context/AppContext';
import { tokenManager } from '../utils/TokenManager';
import { setupApiClient } from '../utils/ApiClient';

const PAGE_SIZE = 20;

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  isDark: boolean;
  onToggleTheme: () => void;
  selectedSession: string | null;
  onSelectSession: (id: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  onToggleCollapse,
  isDark,
  onToggleTheme,
  selectedSession,
  onSelectSession,
}) => {
  const navigate = useNavigate();
  const { refreshSessionsTrigger, setSelectedSession } = useAppContext();

  const handleLogout = () => {
    tokenManager.removeToken();
    setupApiClient();
    setSelectedSession(null);
    navigate('/login', { replace: true });
  };

  const [mode, setMode] = useState<'chat' | 'image'>('chat');
  const [sessions, setSessions] = useState<SessionOut[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);

  const handleModeSwitch = (newMode: 'chat' | 'image') => {
    setMode(newMode);
    if (newMode === 'image') {
      navigate('/image-studio');
    } else {
      navigate('/chat');
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const fetchSessions = useCallback(async (query: string, pg: number) => {
    try {
      const result = await SessionsService.listSessionsApiV1SessionsGet(
        undefined,
        query || undefined,
        pg,
        PAGE_SIZE,
      );
      setSessions(result.items);
      setTotal(result.total);
    } catch (e) {
      console.error('加载会话失败:', e);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- async data fetch; setState runs after await, not synchronously
    fetchSessions(debouncedQuery, page);
  }, [debouncedQuery, page, refreshSessionsTrigger, fetchSessions]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const handleEditStart = (id: string, currentTitle: string) => {
    setEditingId(id);
    setEditingTitle(currentTitle);
  };

  const handleEditSave = async (id: string) => {
    if (!editingTitle.trim()) return;
    try {
      const updated = await SessionsService.updateSessionApiV1SessionsSessionIdPut(id, { title: editingTitle.trim() });
      setSessions((prev) => prev.map((s) => (s.id === id ? updated : s)));
    } catch (e) {
      console.error('更新会话标题失败:', e);
    }
    setEditingId(null);
    setEditingTitle('');
  };

  const handleEditCancel = () => {
    setEditingId(null);
    setEditingTitle('');
  };

  const handleDelete = async (id: string) => {
    try {
      await SessionsService.deleteSessionApiV1SessionsSessionIdDelete(id);
      if (selectedSession === id) {
        setSelectedSession(null);
        navigate('/chat');
      }
      const newTotal = total - 1;
      const newTotalPages = Math.max(1, Math.ceil(newTotal / PAGE_SIZE));
      const targetPage = page > newTotalPages ? newTotalPages : page;
      if (targetPage !== page) {
        setPage(targetPage);
      } else {
        fetchSessions(debouncedQuery, page);
      }
      setTotal(newTotal);
    } catch (e) {
      console.error('删除会话失败:', e);
    }
  };

  const menuItems = [
    { icon: Cpu, label: '模型设置', path: '/llm-settings' },
    { icon: Plug, label: 'MCP 设置', path: '/mcp-settings' },
    { icon: Zap, label: '管理 Agents', path: '/agents' },
    { icon: Clock, label: '定时任务', path: '/scheduled-tasks' },
    { icon: Wrench, label: 'API 工具', path: '/api-tools' },
    { icon: BarChart2, label: '用量统计', path: '/stats' },
    { icon: FileText, label: '提示词模板', path: '/prompt-templates' },
    { icon: Zap, label: '技能管理', path: '/skills' },
    { icon: Brain, label: '记忆管理', path: '/memory' },
    { icon: Network, label: '知识图谱', path: '/knowledge-graph' },
    { icon: Webhook, label: '入站 Webhook', path: '/webhooks' },
    { icon: Eye, label: '界面偏好', path: '/preferences' },
    { icon: HelpCircle, label: '使用帮助', path: '/help' },
  ];

  return (
    <>
      <div
        className={`${collapsed ? 'w-0' : 'w-64'} bg-white dark:bg-zinc-900 transition-all duration-300 overflow-hidden flex flex-col border-r border-gray-200 dark:border-zinc-800 shrink-0`}
      >
        {/* 模式切换 */}
        <div className="p-3 border-b border-gray-200 dark:border-zinc-800">
          <div className="flex gap-1 p-1 bg-gray-100 dark:bg-zinc-800 rounded-xl">
            <button
              onClick={() => handleModeSwitch('chat')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-all ${
                mode === 'chat'
                  ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900 shadow-sm'
                  : 'text-gray-500 dark:text-zinc-400 hover:text-gray-700 dark:hover:text-zinc-200'
              }`}
            >
              <MessageCircle size={13} />
              普通聊天
            </button>
            <button
              onClick={() => handleModeSwitch('image')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-all ${
                mode === 'image'
                  ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900 shadow-sm'
                  : 'text-gray-500 dark:text-zinc-400 hover:text-gray-700 dark:hover:text-zinc-200'
              }`}
            >
              <ImageIcon size={13} />
              文生图
            </button>
          </div>
        </div>

        <div className="px-4 py-3 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between">
          <h2 className="font-semibold text-sm text-gray-900 dark:text-zinc-100">
            {mode === 'chat' ? '对话历史' : '图像工作台'}
          </h2>
          <button
            onClick={onToggleTheme}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-all"
            title={isDark ? '切换到亮色主题' : '切换到暗色主题'}
          >
            {isDark ? (
              <Sun size={16} className="text-gray-500 dark:text-zinc-400" />
            ) : (
              <Moon size={16} className="text-gray-500" />
            )}
          </button>
        </div>

        {mode === 'image' ? (
          <div className="flex-1 flex flex-col p-3 gap-1">
            {[
              { icon: ImageIcon, label: '图像工作台', path: '/image-studio' },
              { icon: GalleryHorizontalEnd, label: '生成历史', path: '/image-gallery' },
              { icon: Wrench, label: '管理文生图模型', path: '/image-tools' },
            ].map(({ icon: Icon, label, path }) => (
              <button
                key={path}
                onClick={() => navigate(path)}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left rounded-xl text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-all"
              >
                <Icon size={15} className="text-gray-500 dark:text-zinc-400 shrink-0" />
                {label}
              </button>
            ))}
          </div>
        ) : (
          <>
            <div className="px-3 py-2">
              <div className="flex items-center gap-2 px-3 py-2 bg-gray-100 dark:bg-zinc-800 rounded-xl border border-gray-200 dark:border-zinc-700">
                <Search size={13} className="text-gray-400 dark:text-zinc-500 shrink-0" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="搜索对话..."
                  className="flex-1 bg-transparent text-sm text-gray-700 dark:text-zinc-300 placeholder-gray-400 dark:placeholder-zinc-500 outline-none"
                />
                {searchQuery && (
                  <button onClick={() => setSearchQuery('')} className="text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300">
                    <X size={13} />
                  </button>
                )}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-2 py-1">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  className={`px-3 py-2.5 my-0.5 rounded-xl transition-all group cursor-pointer ${
                    selectedSession === session.id
                      ? 'bg-gray-100 dark:bg-zinc-800 border-l-2 border-gray-900 dark:border-zinc-100'
                      : 'hover:bg-gray-50 dark:hover:bg-zinc-800/60'
                  }`}
                >
                  {editingId === session.id ? (
                    <div className="flex flex-col gap-2">
                      <input
                        type="text"
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleEditSave(session.id);
                          if (e.key === 'Escape') handleEditCancel();
                        }}
                        className="px-2 py-1 rounded-lg bg-white dark:bg-zinc-700 border border-gray-300 dark:border-zinc-600 text-gray-800 dark:text-zinc-200 text-sm outline-none focus:ring-1 focus:ring-gray-400 dark:focus:ring-zinc-500"
                        placeholder="输入标题..."
                        autoFocus
                      />
                      <div className="flex gap-2 justify-end">
                        <button onClick={() => handleEditSave(session.id)} className="p-1 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition-all" title="保存">
                          <Check size={14} className="text-gray-700 dark:text-zinc-300" />
                        </button>
                        <button onClick={handleEditCancel} className="p-1 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition-all" title="取消">
                          <X size={14} className="text-gray-700 dark:text-zinc-300" />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div
                      onClick={() => {
                        onSelectSession(session.id);
                        navigate(`/chat/${session.id}`);
                      }}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate text-gray-800 dark:text-zinc-200">
                            {session.title}
                          </div>
                          <div className="text-xs text-gray-400 dark:text-zinc-500 mt-0.5">
                            {session.created_at}
                          </div>
                        </div>
                        <div className="ml-2 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-all">
                          <button
                            onClick={(e) => { e.stopPropagation(); handleEditStart(session.id, session.title || ''); }}
                            className="p-1 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition-all"
                            title="编辑标题"
                          >
                            <Edit2 size={12} className="text-gray-500 dark:text-zinc-400" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDelete(session.id); }}
                            className="p-1 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition-all"
                            title="删除"
                          >
                            <Trash2 size={12} className="text-gray-500 dark:text-zinc-400" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {totalPages > 1 && (
              <div className="px-4 py-2 border-t border-gray-200 dark:border-zinc-800 flex items-center justify-between">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 disabled:opacity-30 transition-all"
                >
                  <ChevronUp size={14} className="text-gray-600 dark:text-zinc-400" />
                </button>
                <span className="text-xs text-gray-500 dark:text-zinc-400">{page} / {totalPages}</span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800 disabled:opacity-30 transition-all"
                >
                  <ChevronDown size={14} className="text-gray-600 dark:text-zinc-400" />
                </button>
              </div>
            )}

            <div className="p-3 border-t border-gray-200 dark:border-zinc-800">
              <button
                onClick={() => setMenuOpen((v) => !v)}
                className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded-xl transition-all"
              >
                <span className="text-sm text-gray-700 dark:text-zinc-300">{menuOpen ? '收起' : '更多功能'}</span>
                {menuOpen ? <ChevronUp size={14} className="text-gray-500 dark:text-zinc-400" /> : <ChevronDown size={14} className="text-gray-500 dark:text-zinc-400" />}
              </button>
              <div className={`overflow-hidden transition-all duration-200 ${menuOpen ? 'max-h-80 mt-1.5' : 'max-h-0'}`}>
                <div className="overflow-y-auto max-h-72 space-y-0.5">
                  {menuItems.map(({ icon: Icon, label, path }) => (
                    <button
                      key={path}
                      onClick={() => navigate(path)}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all"
                    >
                      <Icon size={14} className="text-gray-500 dark:text-zinc-400 shrink-0" />
                      {label}
                    </button>
                  ))}
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-all"
                  >
                    <LogOut size={14} className="shrink-0" />
                    退出登录
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* 折叠按钮 */}
      <button
        onClick={onToggleCollapse}
        className="absolute top-6 z-20 p-1.5 bg-white dark:bg-zinc-800 text-gray-600 dark:text-zinc-400 rounded-r-xl hover:bg-gray-50 dark:hover:bg-zinc-700 transition-all border border-l-0 border-gray-200 dark:border-zinc-700 shadow-sm"
        style={{ left: collapsed ? '0' : '256px' }}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </>
  );
};

export default Sidebar;
