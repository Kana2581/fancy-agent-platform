import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Edit2, ChevronDown, ChevronUp, Clock, CheckCircle, XCircle, Loader, Mail, X, Maximize2, Play } from 'lucide-react';
import ThemedSelect from '../components/ThemedSelect';
import { AgentsService } from '../api';
import type { AgentOut } from '../api';
import { ScheduledTasksService } from '../api/services/ScheduledTasksService';
import type { ScheduledTaskOut } from '../api/models/ScheduledTaskOut';
import type { ScheduledTaskCreate } from '../api/models/ScheduledTaskCreate';
import type { ScheduledTaskUpdate } from '../api/models/ScheduledTaskUpdate';
import type { ScheduledTaskExecutionOut } from '../api/models/ScheduledTaskExecutionOut';

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const TIMEZONES = ['Asia/Shanghai', 'Asia/Tokyo', 'Europe/London', 'America/New_York', 'UTC'];

const EMPTY_FORM: ScheduledTaskCreate = {
  agent_id: 0,
  name: '',
  instruction: '',
  schedule_type: 'daily',
  schedule_time: '08:00',
  schedule_day: null,
  timezone: 'Asia/Shanghai',
};

function scheduleLabel(task: ScheduledTaskOut): string {
  const time = task.schedule_time;
  if (task.schedule_type === 'daily') return `每天 ${time}`;
  if (task.schedule_type === 'weekly')
    return `每周${WEEKDAYS[task.schedule_day ?? 0]} ${time}`;
  if (task.schedule_type === 'monthly')
    return `每月 ${task.schedule_day} 日 ${time}`;
  return time;
}

function formatDt(dt: string | null): string {
  if (!dt) return '—';
  const s = dt.endsWith('Z') || dt.includes('+') ? dt : dt + 'Z';
  return new Date(s).toLocaleString('zh-CN');
}

// ── shared input styles ───────────────────────────────────────────────────────
const inputCls =
  'w-full bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-cyan-300/60 placeholder-gray-500/70 text-gray-800';

// ── Modal ────────────────────────────────────────────────────────────────────

interface ModalProps {
  agents: AgentOut[];
  initial?: ScheduledTaskOut | null;
  onClose: () => void;
  onSave: (data: ScheduledTaskCreate | ScheduledTaskUpdate) => Promise<void>;
}

const TaskModal: React.FC<ModalProps> = ({ agents, initial, onClose, onSave }) => {
  const [form, setForm] = useState<ScheduledTaskCreate>(
    initial
      ? {
          agent_id: initial.agent_id,
          name: initial.name,
          instruction: initial.instruction,
          schedule_type: initial.schedule_type as 'daily' | 'weekly' | 'monthly',
          schedule_time: initial.schedule_time,
          schedule_day: initial.schedule_day,
          timezone: initial.timezone,
        }
      : { ...EMPTY_FORM },
  );
  const [saving, setSaving] = useState(false);

  const set = (key: keyof ScheduledTaskCreate, value: unknown) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(form);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 p-4">
      <div className="bg-gray-50 dark:bg-zinc-900 rounded-xl w-full max-w-lg shadow-sm border border-gray-200 dark:border-zinc-700 overflow-hidden">
        {/* Header */}
        <div className="sticky top-0 bg-gray-50 dark:bg-zinc-900 border-b border-gray-200 dark:border-zinc-800 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-800">{initial ? '编辑任务' : '新建定时任务'}</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded-full transition-all">
            <X size={20} className="text-gray-700" />
          </button>
        </div>

        <div className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">任务名称</label>
              <input
                required
                className={inputCls}
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                placeholder="例如：每日天气播报"
              />
            </div>

            {/* Agent */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">选择 Agent</label>
              <ThemedSelect
                value={form.agent_id || ''}
                onChange={(v) => set('agent_id', Number(v))}
                placeholder="请选择…"
                options={agents.map((a) => ({ value: a.id, label: a.description || `Agent #${a.id}` }))}
                className={inputCls}
              />
            </div>

            {/* Instruction */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">指令</label>
              <textarea
                required
                rows={3}
                className={`${inputCls} resize-none`}
                value={form.instruction}
                onChange={(e) => set('instruction', e.target.value)}
                placeholder="输入给 Agent 的指令，例如：查询今天天气和穿衣建议"
              />
            </div>

            {/* Schedule type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">执行频率</label>
              <div className="flex gap-3">
                {(['daily', 'weekly', 'monthly'] as const).map((t) => (
                  <label
                    key={t}
                    className={`flex items-center gap-1.5 cursor-pointer text-sm px-3 py-1.5 rounded-xl border transition-all ${
                      form.schedule_type === t
                        ? 'bg-gray-900 dark:bg-white border-gray-900 dark:border-white text-white dark:text-gray-900 font-medium'
                        : 'bg-gray-50 dark:bg-zinc-900 border-gray-200 dark:border-zinc-800 text-gray-600 hover:bg-gray-100 dark:hover:bg-zinc-700'
                    }`}
                  >
                    <input
                      type="radio"
                      name="schedule_type"
                      value={t}
                      checked={form.schedule_type === t}
                      onChange={() => set('schedule_type', t)}
                      className="sr-only"
                    />
                    {t === 'daily' ? '每天' : t === 'weekly' ? '每周' : '每月'}
                  </label>
                ))}
              </div>
            </div>

            {/* Time + day */}
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">执行时间</label>
                <input
                  type="time"
                  required
                  className={inputCls}
                  value={form.schedule_time}
                  onChange={(e) => set('schedule_time', e.target.value)}
                />
              </div>

              {form.schedule_type === 'weekly' && (
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">星期几</label>
                  <ThemedSelect
                    value={form.schedule_day ?? 0}
                    onChange={(v) => set('schedule_day', Number(v))}
                    options={WEEKDAYS.map((d, i) => ({ value: i, label: d }))}
                    className={inputCls}
                  />
                </div>
              )}

              {form.schedule_type === 'monthly' && (
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-1">几号</label>
                  <ThemedSelect
                    value={form.schedule_day ?? 1}
                    onChange={(v) => set('schedule_day', Number(v))}
                    options={Array.from({ length: 31 }, (_, i) => ({ value: i + 1, label: `${i + 1} 号` }))}
                    className={inputCls}
                  />
                </div>
              )}
            </div>

            {/* Timezone */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">时区</label>
              <ThemedSelect
                value={form.timezone ?? ''}
                onChange={(v) => set('timezone', v)}
                options={TIMEZONES.map((tz) => ({ value: tz, label: tz }))}
                className={inputCls}
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-sm text-gray-700 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 border border-gray-200 dark:border-zinc-700 transition-all"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-5 py-2 rounded-xl text-sm text-white bg- hover:opacity-90 disabled:opacity-50 transition-all font-medium"
              >
                {saving ? '保存中…' : '保存'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

// ── Result detail Modal ──────────────────────────────────────────────────────

interface ResultModalProps {
  result: string;
  onClose: () => void;
}

const ResultModal: React.FC<ResultModalProps> = ({ result, onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 p-4" onClick={onClose}>
    <div
      className="bg-gray-50 dark:bg-zinc-900 rounded-xl w-full max-w-2xl max-h-[80vh] shadow-sm border border-gray-200 dark:border-zinc-700 flex flex-col overflow-hidden"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-900">
        <h3 className="text-base font-semibold text-gray-800">执行结果详情</h3>
        <button onClick={onClose} className="p-2 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded-full transition-all">
          <X size={18} className="text-gray-700" />
        </button>
      </div>
      <div className="p-6 overflow-y-auto flex-1">
        <pre className="text-sm text-gray-700 whitespace-pre-wrap break-words font-sans">{result}</pre>
      </div>
    </div>
  </div>
);

// ── Execution history panel ──────────────────────────────────────────────────

interface ExecutionPanelProps {
  taskId: number;
  refreshNonce?: number;
}

// 轮询配置：每 3 秒一轮，最多约 5 分钟；超过则停止（防止 running 记录卡死导致无限轮询）
const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ROUNDS = 100;

const ExecutionPanel: React.FC<ExecutionPanelProps> = ({ taskId, refreshNonce }) => {
  const [items, setItems] = useState<ScheduledTaskExecutionOut[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [pollTimedOut, setPollTimedOut] = useState(false);
  const [manualTick, setManualTick] = useState(0);
  const [selectedResult, setSelectedResult] = useState<string | null>(null);
  const pageSize = 10;

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let rounds = 0;
    setPollTimedOut(false);

    // run_now 是后台异步执行，记录会先以 running 落库；轮询直到没有 running 状态或达到上限为止
    const fetchOnce = async (showLoading: boolean) => {
      if (showLoading) setLoading(true);
      try {
        const res = await ScheduledTasksService.listExecutionsApiV1ScheduledTasksTaskIdExecutionsGet(taskId, page, pageSize);
        if (cancelled) return;
        setItems(res.items);
        setTotal(res.total);
        if (res.items.some((ex) => ex.status === 'running')) {
          rounds += 1;
          if (rounds >= POLL_MAX_ROUNDS) {
            setPollTimedOut(true);
            return;
          }
          timer = setTimeout(() => fetchOnce(false), POLL_INTERVAL_MS);
        }
      } finally {
        if (showLoading && !cancelled) setLoading(false);
      }
    };

    fetchOnce(true);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [taskId, page, refreshNonce, manualTick]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const statusIcon = (status: string) => {
    if (status === 'success') return <CheckCircle size={14} className="text-green-400" />;
    if (status === 'failed') return <XCircle size={14} className="text-red-400" />;
    return <Loader size={14} className="text-gray-600 dark:text-zinc-300 animate-spin" />;
  };

  return (
    <>
    {selectedResult !== null && (
      <ResultModal result={selectedResult} onClose={() => setSelectedResult(null)} />
    )}
    <div className="mt-3 bg-gray-50 dark:bg-zinc-900 rounded-2xl p-4 border border-gray-200 dark:border-zinc-800 space-y-2">
      <div className="text-xs font-semibold text-gray-500 mb-2">执行历史（共 {total} 条）</div>
      {pollTimedOut && (
        <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-400/10 rounded-lg p-2 border border-amber-300/30">
          <span>任务执行时间较长，已停止自动刷新。</span>
          <button
            onClick={() => setManualTick((n) => n + 1)}
            className="ml-auto px-2 py-0.5 rounded-lg bg-amber-400/20 hover:bg-amber-400/30 transition-all"
          >
            手动刷新
          </button>
        </div>
      )}
      {loading ? (
        <div className="flex items-center gap-2 text-gray-500 text-sm py-2">
          <Loader size={14} className="animate-spin" /> 加载中…
        </div>
      ) : items.length === 0 ? (
        <div className="text-sm text-gray-500 py-2">暂无执行记录</div>
      ) : (
        <div className="space-y-2">
          {items.map((ex) => (
            <div key={ex.id} className="bg-white dark:bg-zinc-900 rounded-xl p-3 text-xs space-y-1 border border-gray-200 dark:border-zinc-800">
              <div className="flex items-center gap-2">
                {statusIcon(ex.status)}
                <span className="font-medium text-gray-700">{ex.status}</span>
                {ex.email_sent && (
                  <span className="flex items-center gap-0.5 text-green-600 ml-1">
                    <Mail size={11} /> 已发邮件
                  </span>
                )}
                <span className="ml-auto text-gray-500">{formatDt(ex.started_at)}</span>
              </div>
              {ex.result && (
                <div className="relative">
                  <div className="text-gray-600 bg-gray-100 dark:bg-zinc-800 rounded-lg p-2 max-h-24 overflow-y-auto whitespace-pre-wrap pr-7">
                    {ex.result}
                  </div>
                  <button
                    onClick={() => setSelectedResult(ex.result!)}
                    className="absolute top-1.5 right-1.5 p-0.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded transition-all"
                    title="查看完整结果"
                  >
                    <Maximize2 size={11} className="text-gray-500" />
                  </button>
                </div>
              )}
              {ex.error && (
                <div className="text-red-500 bg-red-400/10 rounded-lg p-2 border border-red-300/20">{ex.error}</div>
              )}
            </div>
          ))}
          {totalPages > 1 && (
            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-2 py-1 rounded-lg text-gray-600 hover:bg-gray-100 dark:hover:bg-zinc-700 disabled:opacity-30 text-xs transition-all"
              >
                上一页
              </button>
              <span className="text-gray-500 text-xs">{page}/{totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-2 py-1 rounded-lg text-gray-600 hover:bg-gray-100 dark:hover:bg-zinc-700 disabled:opacity-30 text-xs transition-all"
              >
                下一页
              </button>
            </div>
          )}
        </div>
      )}
    </div>
    </>
  );
};

// ── Main page ────────────────────────────────────────────────────────────────

const ScheduledTasksPage: React.FC = () => {
  const [tasks, setTasks] = useState<ScheduledTaskOut[]>([]);
  const [agents, setAgents] = useState<AgentOut[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<ScheduledTaskOut | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [runningIds, setRunningIds] = useState<Set<number>>(new Set());
  const [runRefresh, setRunRefresh] = useState(0);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const [taskList, agentList] = await Promise.all([
      ScheduledTasksService.listTasksApiV1ScheduledTasksGet(),
      AgentsService.listAgentsApiV1AgentsGet(),
    ]);
    setTasks(taskList);
    setAgents(agentList);
  };

  const agentName = (id: number) => {
    const a = agents.find((ag) => ag.id === id);
    return a?.description || `Agent #${id}`;
  };

  const handleCreate = async (data: ScheduledTaskCreate | ScheduledTaskUpdate) => {
    const created = await ScheduledTasksService.createTaskApiV1ScheduledTasksPost(data as ScheduledTaskCreate);
    setTasks((prev) => [created, ...prev]);
  };

  const handleUpdate = async (data: ScheduledTaskCreate | ScheduledTaskUpdate) => {
    if (!editing) return;
    const updated = await ScheduledTasksService.updateTaskApiV1ScheduledTasksTaskIdPut(editing.id, data as ScheduledTaskUpdate);
    setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    setEditing(null);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确认删除该任务？')) return;
    await ScheduledTasksService.deleteTaskApiV1ScheduledTasksTaskIdDelete(id);
    setTasks((prev) => prev.filter((t) => t.id !== id));
    if (expandedId === id) setExpandedId(null);
  };

  const handleToggleEnabled = async (task: ScheduledTaskOut) => {
    const updated = await ScheduledTasksService.updateTaskApiV1ScheduledTasksTaskIdPut(task.id, { is_enabled: !task.is_enabled });
    setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
  };

  const handleRunNow = async (task: ScheduledTaskOut) => {
    setRunningIds((prev) => new Set(prev).add(task.id));
    try {
      await ScheduledTasksService.runTaskNowApiV1ScheduledTasksTaskIdRunPost(task.id);
      // expand history panel so user can see the new execution；并触发刷新（面板已展开时也能重新拉取并轮询）
      setExpandedId(task.id);
      setRunRefresh((n) => n + 1);
    } finally {
      setRunningIds((prev) => { const s = new Set(prev); s.delete(task.id); return s; });
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">定时任务</h1>
            <p className="text-sm text-gray-500 mt-1">配置 Agent 在指定时间自动执行指令，结果通过邮件发送给您</p>
          </div>
          <button
            onClick={() => { setEditing(null); setShowModal(true); }}
            className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-xl text-sm hover:opacity-90 transition-all font-medium"
          >
            <Plus size={16} />
            新建任务
          </button>
        </div>

        {/* Task list */}
        {tasks.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <Clock size={40} className="mx-auto mb-3 opacity-40" />
            <p>暂无定时任务，点击右上角新建</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map((task) => (
              <div
                key={task.id}
                className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-700 overflow-hidden"
              >
                <div className="p-5">
                  <div className="flex items-start gap-3">
                    <Clock
                      size={18}
                      className={`mt-0.5 shrink-0 ${task.is_enabled ? 'text-gray-600 dark:text-zinc-400' : 'text-gray-400'}`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-gray-800">{task.name}</span>
                        <span className="text-xs bg-gray-200 dark:bg-zinc-700 text-gray-700 dark:text-zinc-300 border border-cyan-300/30 px-2 py-0.5 rounded-full">
                          {scheduleLabel(task)}
                        </span>
                        <span className="text-xs text-gray-500">{agentName(task.agent_id)}</span>
                      </div>
                      <p className="text-sm text-gray-500 mt-1 truncate">{task.instruction}</p>
                      <div className="flex gap-4 mt-1.5 text-xs text-gray-400">
                        <span>下次执行：{formatDt(task.next_run_at)}</span>
                        {task.last_run_at && <span>上次执行：{formatDt(task.last_run_at)}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {/* Run now */}
                      <button
                        onClick={() => handleRunNow(task)}
                        disabled={runningIds.has(task.id)}
                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-xl transition-all disabled:opacity-50"
                        title="立即执行"
                      >
                        {runningIds.has(task.id)
                          ? <Loader size={14} className="text-gray-600 dark:text-zinc-400 animate-spin" />
                          : <Play size={14} className="text-gray-700 dark:text-zinc-300" />}
                      </button>
                      {/* Enable toggle */}
                      <button
                        onClick={() => handleToggleEnabled(task)}
                        title={task.is_enabled ? '点击禁用' : '点击启用'}
                        className={`relative w-10 h-5 rounded-full transition-colors ${task.is_enabled ? 'bg-' : 'bg-gray-200 dark:bg-zinc-700 border border-gray-200 dark:border-zinc-700'}`}
                      >
                        <span
                          className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${task.is_enabled ? 'translate-x-5' : 'translate-x-0'}`}
                        />
                      </button>
                      <button
                        onClick={() => { setEditing(task); setShowModal(true); }}
                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-xl transition-all"
                        title="编辑"
                      >
                        <Edit2 size={14} className="text-gray-600" />
                      </button>
                      <button
                        onClick={() => handleDelete(task.id)}
                        className="p-1.5 hover:bg-red-400/20 rounded-xl transition-all"
                        title="删除"
                      >
                        <Trash2 size={14} className="text-red-400" />
                      </button>
                      <button
                        onClick={() => setExpandedId(expandedId === task.id ? null : task.id)}
                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-xl transition-all"
                        title="执行历史"
                      >
                        {expandedId === task.id ? (
                          <ChevronUp size={14} className="text-gray-600" />
                        ) : (
                          <ChevronDown size={14} className="text-gray-600" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>

                {expandedId === task.id && (
                  <div className="border-t border-gray-200 dark:border-zinc-800 px-5 pb-5">
                    <ExecutionPanel taskId={task.id} refreshNonce={runRefresh} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <TaskModal
          agents={agents}
          initial={editing}
          onClose={() => { setShowModal(false); setEditing(null); }}
          onSave={editing ? handleUpdate : handleCreate}
        />
      )}
    </div>
  );
};

export default ScheduledTasksPage;
