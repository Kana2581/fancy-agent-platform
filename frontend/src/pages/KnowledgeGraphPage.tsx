import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Plus, Trash2, X, Network, Search, Sparkles, ChevronRight, ChevronLeft, Edit2, Check, Download } from 'lucide-react';
import {
  ReactFlow, Background, Controls, MiniMap, Panel,
  useNodesState, useEdgesState, useReactFlow,
  Handle, Position,
  type Node, type Edge, type NodeTypes,
} from '@xyflow/react';
import dagre from '@dagrejs/dagre';
import type { KGNodeOut, KGEdgeOut, KGGraphOut, AgentOut } from '../api';
import { KnowledgeGraphService, AgentsService } from '../api';
import type { KGNodeCreate, KGNodeUpdate, KGEdgeCreate, KGExtractPreview } from '../api';

// ============ Type colors ============
const TYPE_COLORS: Record<string, string> = {
  person: 'bg-pink-500/25 text-pink-100 border-pink-400/50',
  organization: 'bg-gray-200 dark:bg-zinc-700 text-gray-700 dark:text-zinc-300 border-gray-300 dark:border-zinc-600',
  place: 'bg-gray-200 dark:bg-zinc-700 text-gray-700 dark:text-zinc-300 border-gray-300 dark:border-zinc-600',
  concept: 'bg-gray-200 dark:bg-zinc-700 text-gray-700 dark:text-zinc-300 border-gray-300 dark:border-zinc-600',
  event: 'bg-amber-500/25 text-amber-100 border-amber-400/50',
  product: 'bg-gray-200 dark:bg-zinc-700 text-gray-600 dark:text-zinc-400 border-gray-300 dark:border-zinc-600',
};
function typeColor(type: string) {
  return TYPE_COLORS[type.toLowerCase()] ?? 'bg-slate-500/25 text-slate-100 border-slate-400/50';
}

const TYPE_DOT_COLORS: Record<string, string> = {
  person: '#f472b6',
  organization: '#60a5fa',
  place: '#34d399',
  concept: '#a78bfa',
  event: '#fbbf24',
  product: '#22d3ee',
};
function dotColor(type: string) {
  return TYPE_DOT_COLORS[type?.toLowerCase()] ?? '#94a3b8';
}

// ============ React Flow custom node ============
function KGCustomNode({ data }: { data: Record<string, unknown> }) {
  const label = data.label as string;
  const type = data.type as string;
  const highlighted = data.highlighted as boolean;
  const dimmed = data.dimmed as boolean;
  const color = dotColor(type);
  const handleStyle = { background: color, border: 'none', width: 8, height: 8 };
  return (
    <div
      style={{
        border: `2px solid ${dimmed ? `${color}30` : color}`,
        background: highlighted ? 'rgba(15,23,42,0.97)' : dimmed ? 'rgba(15,23,42,0.35)' : 'rgba(15,23,42,0.80)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        boxShadow: highlighted
          ? `0 0 22px ${color}90, 0 6px 24px ${color}50, 0 2px 10px rgba(0,0,0,0.4)`
          : `0 6px 24px ${color}40, 0 2px 10px rgba(0,0,0,0.4)`,
        opacity: dimmed ? 0.3 : 1,
        transition: 'all 0.2s ease',
      }}
      className="rounded-2xl px-5 py-3 min-w-[110px] text-center"
    >
      <Handle type="target" position={Position.Top} style={handleStyle} />
      <div className="text-xs font-bold mb-1 tracking-wide" style={{ color: dimmed ? `${color}50` : color }}>{type}</div>
      <div className="text-base font-bold leading-tight" style={{ color: dimmed ? 'rgba(248,250,252,0.35)' : '#f8fafc' }}>{label}</div>
      <Handle type="source" position={Position.Bottom} style={handleStyle} />
    </div>
  );
}

const nodeTypes: NodeTypes = { kgNode: KGCustomNode };

// ============ Layout helper (dagre) ============
const NODE_WIDTH = 160;
const NODE_HEIGHT = 60;

function getLayoutedElements(nodes: Node[], edges: Edge[], direction: 'LR' | 'TB'): Node[] {
  if (nodes.length === 0) return nodes;
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, nodesep: 60, ranksep: 100, marginx: 40, marginy: 40 });
  nodes.forEach(n => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach(e => {
    if (g.hasNode(e.source) && g.hasNode(e.target)) g.setEdge(e.source, e.target);
  });
  dagre.layout(g);
  return nodes.map(n => {
    const pos = g.node(n.id);
    return { ...n, position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 } };
  });
}

function toFlowData(
  kgNodes: KGNodeOut[],
  kgEdges: KGEdgeOut[],
  direction: 'LR' | 'TB' = 'LR',
  hiddenTypes: Set<string> = new Set(),
): { nodes: Node[]; edges: Edge[] } {
  const visibleIds = new Set(kgNodes.filter(n => !hiddenTypes.has(n.type)).map(n => String(n.id)));

  const rawNodes: Node[] = kgNodes.map(n => ({
    id: String(n.id),
    type: 'kgNode',
    position: { x: 0, y: 0 },
    hidden: !visibleIds.has(String(n.id)),
    data: { label: n.name, type: n.type, highlighted: false, dimmed: false },
  }));

  const rawEdges: Edge[] = kgEdges.map(e => ({
    id: String(e.id),
    source: String(e.source_node_id),
    target: String(e.target_node_id),
    label: e.relation,
    type: 'smoothstep',
    hidden: !visibleIds.has(String(e.source_node_id)) || !visibleIds.has(String(e.target_node_id)),
    animated: false,
    style: { stroke: 'rgba(148,163,184,0.7)', strokeWidth: 2 },
    labelStyle: { fill: '#f1f5f9', fontSize: 13, fontWeight: 600 },
    labelBgStyle: { fill: 'rgba(30,30,30,0.90)' },
    labelBgPadding: [4, 7] as [number, number],
    labelBgBorderRadius: 8,
  }));

  const visibleNodes = rawNodes.filter(n => !n.hidden);
  const visibleEdges = rawEdges.filter(e => !e.hidden);
  const layoutedVisible = getLayoutedElements(visibleNodes, visibleEdges, direction);
  const layoutMap = Object.fromEntries(layoutedVisible.map(n => [n.id, n]));
  const nodes = rawNodes.map(n => layoutMap[n.id] ?? n);

  return { nodes, edges: rawEdges };
}

// ============ KGGraphView ============
interface KGGraphViewProps {
  kgNodes: KGNodeOut[];
  kgEdges: KGEdgeOut[];
}

// Sub-component: jump to a node using useReactFlow (must be inside ReactFlow tree)
function JumpToNode({ nodeId, rfNodes }: { nodeId: string | null; rfNodes: Node[] }) {
  const { setCenter } = useReactFlow();
  const prevId = useRef<string | null>(null);
  useEffect(() => {
    if (!nodeId || nodeId === prevId.current) return;
    prevId.current = nodeId;
    const n = rfNodes.find(nd => nd.id === nodeId);
    if (n) setCenter(n.position.x + NODE_WIDTH / 2, n.position.y + NODE_HEIGHT / 2, { zoom: 1.5, duration: 600 });
  }, [nodeId, rfNodes, setCenter]);
  return null;
}

const KGGraphView: React.FC<KGGraphViewProps> = ({ kgNodes, kgEdges }) => {
  const [direction, setDirection] = useState<'LR' | 'TB'>('LR');
  const [searchQuery, setSearchQuery] = useState('');
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set());
  const [jumpToId, setJumpToId] = useState<string | null>(null);

  const allTypes = useMemo(() => Array.from(new Set(kgNodes.map(n => n.type))), [kgNodes]);

  const init = toFlowData(kgNodes, kgEdges, direction, hiddenTypes);
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState(init.nodes);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState(init.edges);

  // Re-layout when data, direction, or hidden types change
  useEffect(() => {
    const { nodes, edges } = toFlowData(kgNodes, kgEdges, direction, hiddenTypes);
    setRfNodes(nodes);
    setRfEdges(edges);
  }, [kgNodes, kgEdges, direction, hiddenTypes, setRfNodes, setRfEdges]);

  // Update highlight/dim styling when search query changes (no re-layout)
  useEffect(() => {
    const q = searchQuery.toLowerCase().trim();
    setRfNodes(nds => nds.map(n => ({
      ...n,
      data: {
        ...n.data,
        highlighted: q ? (n.data.label as string).toLowerCase().includes(q) : false,
        dimmed: q ? !(n.data.label as string).toLowerCase().includes(q) : false,
      },
    })));
  }, [searchQuery, setRfNodes]);

  // Auto-jump when exactly one node matches
  useEffect(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) { setJumpToId(null); return; }
    const matches = kgNodes.filter(n => n.name.toLowerCase().includes(q));
    setJumpToId(matches.length === 1 ? String(matches[0].id) : null);
  }, [searchQuery, kgNodes]);

  const handleRelayout = useCallback(() => {
    const { nodes, edges } = toFlowData(kgNodes, kgEdges, direction, hiddenTypes);
    setRfNodes(nodes);
    setRfEdges(edges);
  }, [kgNodes, kgEdges, direction, hiddenTypes, setRfNodes, setRfEdges]);

  const toggleType = useCallback((type: string) => {
    setHiddenTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type); else next.add(type);
      return next;
    });
  }, []);

  if (kgNodes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4">🕸️</div>
          <p className="text-base text-gray-600">图谱中还没有节点</p>
          <p className="text-sm text-gray-500 mt-1">先在「实体节点」标签页添加节点</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-4 overflow-hidden">
      <div className="w-full h-full rounded-xl overflow-hidden border border-gray-200 dark:border-zinc-800" style={{ background: 'rgba(10,15,30,0.82)' }}>
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="rgba(255,255,255,0.06)" gap={28} size={1.5} />
          <Controls className="!bg-white dark:!bg-zinc-900 !border-gray-200 dark:!border-zinc-800 !rounded-xl !shadow-sm" />
          <MiniMap
            nodeColor={n => dotColor((n.data as Record<string, unknown>).type as string)}
            className="!bg-white dark:!bg-zinc-900 !border-gray-200 dark:!border-zinc-800 !rounded-xl"
            maskColor="rgba(15,23,42,0.5)"
          />

          {/* Search overlay – top-left */}
          <Panel position="top-left" style={{ margin: 12 }}>
            <div className="flex items-center gap-2 px-3 py-2 rounded-2xl border border-gray-200 dark:border-zinc-800"
              style={{ background: 'rgba(10,15,30,0.85)', backdropFilter: 'blur(20px)' }}>
              <Search size={13} className="text-gray-400 shrink-0" />
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="搜索节点..."
                className="bg-transparent text-sm text-gray-200 placeholder-gray-500 outline-none w-32"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="text-gray-500 hover:text-gray-300 transition">
                  <X size={12} />
                </button>
              )}
            </div>
          </Panel>

          {/* Layout controls + type legend – top-right */}
          <Panel position="top-right" style={{ margin: 12, display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-end' }}>
            {/* Direction toggle + re-layout */}
            <div className="flex gap-1 p-1 rounded-2xl border border-gray-200 dark:border-zinc-800"
              style={{ background: 'rgba(10,15,30,0.85)', backdropFilter: 'blur(20px)' }}>
              <button
                onClick={() => setDirection('LR')}
                title="左右布局"
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${direction === 'LR' ? 'bg-gray-200 dark:bg-zinc-700 text-gray-700 dark:text-zinc-100 border border-gray-300 dark:border-zinc-600' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-50 dark:bg-zinc-900'}`}
              >↔ LR</button>
              <button
                onClick={() => setDirection('TB')}
                title="上下布局"
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${direction === 'TB' ? 'bg-gray-200 dark:bg-zinc-700 text-gray-700 dark:text-zinc-100 border border-gray-300 dark:border-zinc-600' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-50 dark:bg-zinc-900'}`}
              >↕ TB</button>
              <button
                onClick={handleRelayout}
                title="重新布局"
                className="px-3 py-1.5 rounded-xl text-xs font-semibold text-gray-400 hover:text-gray-200 hover:bg-gray-50 dark:bg-zinc-900 transition-all"
              >⟳</button>
            </div>

            {/* Type legend */}
            {allTypes.length > 0 && (
              <div className="flex flex-col gap-0.5 p-2 rounded-2xl border border-gray-200 dark:border-zinc-800"
                style={{ background: 'rgba(10,15,30,0.85)', backdropFilter: 'blur(20px)' }}>
                {allTypes.map(type => {
                  const hidden = hiddenTypes.has(type);
                  return (
                    <button
                      key={type}
                      onClick={() => toggleType(type)}
                      className={`flex items-center gap-2 px-2 py-1 rounded-xl text-xs font-medium transition-all hover:bg-gray-50 dark:bg-zinc-900 ${hidden ? 'opacity-35' : 'opacity-100'}`}
                    >
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: dotColor(type) }} />
                      <span className="text-gray-300">{type}</span>
                      {hidden && <span className="ml-1 text-gray-600 text-[10px]">隐</span>}
                    </button>
                  );
                })}
              </div>
            )}
          </Panel>

          <JumpToNode nodeId={jumpToId} rfNodes={rfNodes} />
        </ReactFlow>
      </div>
    </div>
  );
};

// ============ Node Modal ============
interface NodeModalProps {
  editing: KGNodeOut | null;
  onClose: () => void;
  onSave: (data: KGNodeCreate | KGNodeUpdate) => Promise<void>;
}

const NodeModal: React.FC<NodeModalProps> = ({ editing, onClose, onSave }) => {
  const [name, setName] = useState(editing?.name ?? '');
  const [type, setType] = useState(editing?.type ?? 'concept');
  const [desc, setDesc] = useState(editing?.description ?? '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    await onSave({ name: name.trim(), type: type.trim() || 'concept', description: desc.trim() || null });
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-50 dark:bg-zinc-900  rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 w-full max-w-md">
        <div className="flex items-center justify-between p-6 pb-4 border-b border-gray-200 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg- rounded-2xl flex items-center justify-center">
              <Network size={18} className="text-white" />
            </div>
            <h3 className="text-xl font-bold text-gray-800">{editing ? '编辑节点' : '添加节点'}</h3>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-black/10 rounded-xl transition"><X size={20} /></button>
        </div>
        <div className="px-6 pb-6 pt-4 space-y-4">
          <div>
            <label className="text-base font-medium text-gray-700 mb-1 block">名称 <span className="text-red-500">*</span></label>
            <input
              value={name} onChange={e => setName(e.target.value)}
              placeholder="如：OpenAI、人工智能、北京..."
              className="w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800 placeholder-gray-500"
            />
          </div>
          <div>
            <label className="text-base font-medium text-gray-700 mb-1 block">类型</label>
            <input
              value={type} onChange={e => setType(e.target.value)}
              placeholder="person / organization / place / concept / event..."
              className="w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800 placeholder-gray-500"
            />
          </div>
          <div>
            <label className="text-base font-medium text-gray-700 mb-1 block">描述</label>
            <textarea
              value={desc} onChange={e => setDesc(e.target.value)}
              placeholder="可选，简短描述该实体..."
              rows={3}
              className="w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800 placeholder-gray-500 resize-none"
            />
          </div>
          <div className="flex gap-3 pt-1">
            <button onClick={onClose} className="flex-1 py-2.5 bg-gray-200 dark:bg-zinc-700 hover:bg-white/40 text-gray-700 rounded-2xl font-medium transition">取消</button>
            <button
              onClick={handleSave} disabled={saving || !name.trim()}
              className="flex-1 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl font-medium disabled:opacity-50 transition"
            >
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============ Edge Modal ============
interface EdgeModalProps {
  nodes: KGNodeOut[];
  onClose: () => void;
  onSave: (data: KGEdgeCreate) => Promise<void>;
}

const EdgeModal: React.FC<EdgeModalProps> = ({ nodes, onClose, onSave }) => {
  const [sourceId, setSourceId] = useState('');
  const [targetId, setTargetId] = useState('');
  const [relation, setRelation] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!sourceId || !targetId || !relation.trim()) return;
    setSaving(true);
    await onSave({ source_node_id: Number(sourceId), target_node_id: Number(targetId), relation: relation.trim() });
    setSaving(false);
  };

  const selectClass = "w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-50 dark:bg-zinc-900  rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 w-full max-w-md">
        <div className="flex items-center justify-between p-6 pb-4 border-b border-gray-200 dark:border-zinc-800">
          <h3 className="text-xl font-bold text-gray-800">添加关系边</h3>
          <button onClick={onClose} className="p-2 hover:bg-black/10 rounded-xl transition"><X size={20} /></button>
        </div>
        <div className="px-6 pb-6 pt-4 space-y-4">
          <div>
            <label className="text-base font-medium text-gray-700 mb-1 block">起点实体 <span className="text-red-500">*</span></label>
            <select value={sourceId} onChange={e => setSourceId(e.target.value)} className={selectClass}>
              <option value="">请选择起点...</option>
              {nodes.map(n => <option key={n.id} value={n.id}>{n.name} [{n.type}]</option>)}
            </select>
          </div>
          <div>
            <label className="text-base font-medium text-gray-700 mb-1 block">关系标签 <span className="text-red-500">*</span></label>
            <input
              value={relation} onChange={e => setRelation(e.target.value)}
              placeholder="如：创立、属于、合作、位于..."
              className="w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800 placeholder-gray-500"
            />
          </div>
          <div>
            <label className="text-base font-medium text-gray-700 mb-1 block">终点实体 <span className="text-red-500">*</span></label>
            <select value={targetId} onChange={e => setTargetId(e.target.value)} className={selectClass}>
              <option value="">请选择终点...</option>
              {nodes.map(n => <option key={n.id} value={n.id}>{n.name} [{n.type}]</option>)}
            </select>
          </div>
          <div className="flex gap-3 pt-1">
            <button onClick={onClose} className="flex-1 py-2.5 bg-gray-200 dark:bg-zinc-700 hover:bg-white/40 text-gray-700 rounded-2xl font-medium transition">取消</button>
            <button
              onClick={handleSave} disabled={saving || !sourceId || !targetId || !relation.trim()}
              className="flex-1 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl font-medium disabled:opacity-50 transition"
            >
              {saving ? '保存中...' : '添加'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============ Extract Modal ============
interface ExtractModalProps {
  graphId: number;
  agents: AgentOut[];
  onClose: () => void;
  onConfirm: (preview: KGExtractPreview) => Promise<void>;
}

const ExtractModal: React.FC<ExtractModalProps> = ({ graphId, agents, onClose, onConfirm }) => {
  const [text, setText] = useState('');
  const [agentId, setAgentId] = useState(agents[0]?.id?.toString() ?? '');
  const [preview, setPreview] = useState<KGExtractPreview | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleExtract = async () => {
    if (!text.trim() || !agentId) return;
    setExtracting(true);
    setError('');
    setPreview(null);
    try {
      const result = await KnowledgeGraphService.extractFromText(graphId, text.trim(), Number(agentId));
      setPreview(result);
    } catch (e: any) {
      setError(e?.body?.detail || '提取失败，请重试');
    } finally {
      setExtracting(false);
    }
  };

  const handleConfirm = async () => {
    if (!preview) return;
    setSaving(true);
    await onConfirm(preview);
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-50 dark:bg-zinc-900  rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 pb-4 border-b border-gray-200 dark:border-zinc-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-200 dark:bg-zinc-700 rounded-2xl flex items-center justify-center">
              <Sparkles size={18} className="text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-800">从文本提取知识图谱</h3>
              <p className="text-xs text-gray-500 mt-0.5">使用 Agent 的 LLM 自动识别实体和关系</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-black/10 rounded-xl transition"><X size={20} /></button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          <div>
            <label className="text-base font-medium text-gray-700 mb-1 block">使用 Agent 的 LLM <span className="text-red-500">*</span></label>
            <select
              value={agentId} onChange={e => setAgentId(e.target.value)}
              className="w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-violet-400/50 text-gray-800"
            >
              {agents.length === 0 && <option value="">暂无可用 Agent</option>}
              {agents.map(a => <option key={a.id} value={a.id}>{a.description || `Agent #${a.id}`}</option>)}
            </select>
          </div>

          <div>
            <label className="text-base font-medium text-gray-700 mb-1 block">输入文本 <span className="text-red-500">*</span></label>
            <textarea
              value={text} onChange={e => setText(e.target.value)}
              placeholder="粘贴需要提取知识图谱的文本..."
              rows={6}
              className="w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-violet-400/50 text-gray-800 placeholder-gray-500 resize-none"
            />
          </div>

          <button
            onClick={handleExtract} disabled={extracting || !text.trim() || !agentId}
            className="w-full py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl font-medium disabled:opacity-50 transition flex items-center justify-center gap-2"
          >
            <Sparkles size={16} />
            {extracting ? '提取中...' : '开始提取'}
          </button>

          {error && <p className="text-sm text-red-500 bg-red-50/50 rounded-xl px-4 py-2">{error}</p>}

          {preview && (
            <div className="space-y-3">
              <div className="h-px bg-gray-100 dark:bg-zinc-800" />
              <p className="text-base font-semibold text-gray-700">提取结果预览</p>
              <div className="bg-gray-50 dark:bg-zinc-900 rounded-2xl p-4 space-y-2">
                <p className="text-sm font-semibold text-gray-600">节点 ({preview.nodes.length})</p>
                {preview.nodes.length === 0
                  ? <p className="text-sm text-gray-500">无</p>
                  : preview.nodes.map((n, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <span className={`px-2.5 py-0.5 rounded-full border text-xs font-semibold ${typeColor(n.type)}`}>{n.type}</span>
                      <span className="text-gray-800 font-semibold">{n.name}</span>
                      {n.description && <span className="text-gray-500 text-sm truncate">— {n.description}</span>}
                    </div>
                  ))
                }
              </div>
              <div className="bg-gray-50 dark:bg-zinc-900 rounded-2xl p-4 space-y-2">
                <p className="text-sm font-semibold text-gray-600">关系 ({preview.edges.length})</p>
                {preview.edges.length === 0
                  ? <p className="text-sm text-gray-500">无</p>
                  : preview.edges.map((e, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-sm text-gray-700">
                      <span className="font-semibold">{e.source_name}</span>
                      <ChevronRight size={13} className="text-gray-600 dark:text-zinc-300 shrink-0" />
                      <span className="px-2.5 py-0.5 rounded-full bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 text-gray-600 dark:text-zinc-300 text-xs font-semibold">{e.relation}</span>
                      <ChevronRight size={13} className="text-gray-600 dark:text-zinc-300 shrink-0" />
                      <span className="font-semibold">{e.target_name}</span>
                    </div>
                  ))
                }
              </div>
            </div>
          )}
        </div>

        <div className="p-6 pt-4 border-t border-gray-200 dark:border-zinc-800 flex gap-3 shrink-0">
          <button onClick={onClose} className="flex-1 py-2.5 bg-gray-200 dark:bg-zinc-700 hover:bg-white/40 text-gray-700 rounded-2xl font-medium transition">取消</button>
          <button
            onClick={handleConfirm} disabled={!preview || saving}
            className="flex-1 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl font-medium disabled:opacity-50 transition"
          >
            {saving ? '保存中...' : '确认保存'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ============ Main Page ============
const KnowledgeGraphPage: React.FC = () => {
  const [graphs, setGraphs] = useState<KGGraphOut[]>([]);
  const [selectedGraph, setSelectedGraph] = useState<KGGraphOut | null>(null);
  const [nodes, setNodes] = useState<KGNodeOut[]>([]);
  const [edges, setEdges] = useState<KGEdgeOut[]>([]);
  const [agents, setAgents] = useState<AgentOut[]>([]);
  const [loadingGraphs, setLoadingGraphs] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [tab, setTab] = useState<'nodes' | 'edges' | 'graph'>('nodes');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  // Graph creation
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [editingGraph, setEditingGraph] = useState<KGGraphOut | null>(null);
  const [editName, setEditName] = useState('');

  // Modals
  const [nodeModal, setNodeModal] = useState<{ open: boolean; editing: KGNodeOut | null }>({ open: false, editing: null });
  const [edgeModal, setEdgeModal] = useState(false);
  const [extractModal, setExtractModal] = useState(false);

  // Load graphs and agents on mount
  useEffect(() => {
    Promise.all([
      KnowledgeGraphService.listGraphs(),
      AgentsService.listAgentsApiV1AgentsGet(),
    ]).then(([gs, as]) => {
      setGraphs(gs);
      setAgents(as);
      if (gs.length > 0) setSelectedGraph(gs[0]);
    }).catch(console.error).finally(() => setLoadingGraphs(false));
  }, []);

  // Load nodes & edges when selected graph changes
  const loadContent = useCallback(async (graph: KGGraphOut) => {
    setLoadingContent(true);
    setNodes([]);
    setEdges([]);
    try {
      const [ns, es] = await Promise.all([
        KnowledgeGraphService.listNodes(graph.id),
        KnowledgeGraphService.listEdges(graph.id),
      ]);
      setNodes(ns);
      setEdges(es);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingContent(false);
    }
  }, []);

  useEffect(() => {
    if (selectedGraph) {
      setSearch('');
      setTypeFilter('');
      setTab('nodes');
      loadContent(selectedGraph);
    }
  }, [selectedGraph, loadContent]);

  // ---- Graph CRUD ----
  const handleCreateGraph = async () => {
    if (!newName.trim()) return;
    const g = await KnowledgeGraphService.createGraph({ name: newName.trim() });
    setGraphs(prev => [...prev, g]);
    setSelectedGraph(g);
    setNewName('');
    setCreating(false);
  };

  const handleUpdateGraph = async (graph: KGGraphOut) => {
    if (!editName.trim()) return;
    const updated = await KnowledgeGraphService.updateGraph(graph.id, { name: editName.trim() });
    setGraphs(prev => prev.map(g => g.id === updated.id ? updated : g));
    if (selectedGraph?.id === updated.id) setSelectedGraph(updated);
    setEditingGraph(null);
  };

  const handleDeleteGraph = async (graph: KGGraphOut) => {
    if (!confirm(`确定删除图谱「${graph.name}」？其中所有节点和边都会被删除。`)) return;
    await KnowledgeGraphService.deleteGraph(graph.id);
    const remaining = graphs.filter(g => g.id !== graph.id);
    setGraphs(remaining);
    if (selectedGraph?.id === graph.id) {
      setSelectedGraph(remaining[0] ?? null);
    }
  };

  // ---- Node CRUD ----
  const handleNodeSave = async (data: KGNodeCreate | KGNodeUpdate) => {
    if (!selectedGraph) return;
    if (nodeModal.editing) {
      const updated = await KnowledgeGraphService.updateNode(nodeModal.editing.id, data as KGNodeUpdate);
      setNodes(prev => prev.map(n => n.id === updated.id ? updated : n));
    } else {
      const created = await KnowledgeGraphService.createNode(selectedGraph.id, data as KGNodeCreate);
      setNodes(prev => [created, ...prev]);
    }
    setNodeModal({ open: false, editing: null });
  };

  const handleNodeDelete = async (node: KGNodeOut) => {
    if (!confirm(`确定删除实体「${node.name}」？相关的关系边也会被删除。`)) return;
    await KnowledgeGraphService.deleteNode(node.id);
    setNodes(prev => prev.filter(n => n.id !== node.id));
    setEdges(prev => prev.filter(e => e.source_node_id !== node.id && e.target_node_id !== node.id));
  };

  // ---- Edge CRUD ----
  const handleEdgeSave = async (data: KGEdgeCreate) => {
    if (!selectedGraph) return;
    const created = await KnowledgeGraphService.createEdge(selectedGraph.id, data);
    setEdges(prev => [created, ...prev]);
    setEdgeModal(false);
  };

  const handleEdgeDelete = async (edge: KGEdgeOut) => {
    if (!confirm('确定删除这条关系边吗？')) return;
    await KnowledgeGraphService.deleteEdge(edge.id);
    setEdges(prev => prev.filter(e => e.id !== edge.id));
  };

  // ---- Export Cypher ----
  const [exporting, setExporting] = useState(false);
  const handleExportCypher = async () => {
    if (!selectedGraph || exporting) return;
    setExporting(true);
    try {
      const text = await KnowledgeGraphService.exportCypher(selectedGraph.id);
      const safeName = selectedGraph.name.replace(/[^\w\-]+/g, '_') || `graph-${selectedGraph.id}`;
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${safeName}.cypher`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      alert('导出失败，请重试');
    } finally {
      setExporting(false);
    }
  };

  // ---- Extract & save ----
  const handleExtractConfirm = async (preview: KGExtractPreview) => {
    if (!selectedGraph) return;
    for (const n of preview.nodes) {
      try {
        const existing = nodes.find(nd => nd.name === n.name);
        if (existing) continue;
        const created = await KnowledgeGraphService.createNode(selectedGraph.id, { name: n.name, type: n.type, description: n.description });
        setNodes(prev => [created, ...prev]);
      } catch { /* 同名已存在，忽略 */ }
    }
    const latestNodes = await KnowledgeGraphService.listNodes(selectedGraph.id);
    setNodes(latestNodes);
    const nameMap = Object.fromEntries(latestNodes.map(n => [n.name, n.id]));
    for (const e of preview.edges) {
      const srcId = nameMap[e.source_name ?? ''];
      const tgtId = nameMap[e.target_name ?? ''];
      if (!srcId || !tgtId) continue;
      try {
        const created = await KnowledgeGraphService.createEdge(selectedGraph.id, { source_node_id: srcId, target_node_id: tgtId, relation: e.relation });
        setEdges(prev => [created, ...prev]);
      } catch { /* 重复边，忽略 */ }
    }
    setExtractModal(false);
  };

  const filteredNodes = nodes.filter(n => {
    const matchSearch = !search || n.name.includes(search) || (n.description ?? '').includes(search);
    const matchType = !typeFilter || n.type === typeFilter;
    return matchSearch && matchType;
  });

  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n.name]));
  const allTypes = Array.from(new Set(nodes.map(n => n.type))).sort();

  return (
    <div className="flex h-full overflow-hidden">
      {/* ======== Left sidebar: graph list ======== */}
      <div className={`shrink-0 flex flex-col border-r border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-800/30 overflow-hidden transition-all duration-300 ${sidebarCollapsed ? 'w-12' : 'w-60'}`}>
        <div className="p-3 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between shrink-0">
          {!sidebarCollapsed && (
            <div className="flex items-center gap-2">
              <Network size={18} className="text-gray-600" />
              <span className="text-base font-semibold text-gray-700">我的图谱</span>
            </div>
          )}
          <div className={`flex items-center gap-1 ${sidebarCollapsed ? 'w-full justify-center' : ''}`}>
            {!sidebarCollapsed && (
              <button
                onClick={() => { setCreating(true); setNewName(''); }}
                className="p-1.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition"
                title="新建图谱"
              >
                <Plus size={15} className="text-gray-600" />
              </button>
            )}
            <button
              onClick={() => setSidebarCollapsed(v => !v)}
              className="p-1.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition"
              title={sidebarCollapsed ? '展开侧栏' : '收起侧栏'}
            >
              {sidebarCollapsed ? <ChevronRight size={15} className="text-gray-600" /> : <ChevronLeft size={15} className="text-gray-600" />}
            </button>
          </div>
        </div>

        {sidebarCollapsed ? (
          /* Collapsed: show colored dots for each graph */
          <div className="flex-1 overflow-y-auto py-2 flex flex-col items-center gap-2">
            {graphs.map(g => (
              <button
                key={g.id}
                onClick={() => { setSelectedGraph(g); setSidebarCollapsed(false); }}
                title={g.name}
                className={`w-7 h-7 rounded-full border-2 transition-all flex items-center justify-center text-[10px] font-bold text-white ${
                  selectedGraph?.id === g.id
                    ? 'bg- border-cyan-400/60 shadow-md'
                    : 'bg-gray-200 dark:bg-zinc-700 border-gray-200 dark:border-zinc-700 hover:bg-gray-50 dark:bg-zinc-800/300 text-gray-600'
                }`}
              >
                {g.name.charAt(0).toUpperCase()}
              </button>
            ))}
            <button
              onClick={() => { setSidebarCollapsed(false); setCreating(true); setNewName(''); }}
              title="新建图谱"
              className="w-7 h-7 rounded-full border-2 border-dashed border-white/40 hover:bg-gray-100 dark:hover:bg-zinc-700 transition flex items-center justify-center"
            >
              <Plus size={12} className="text-gray-500" />
            </button>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {/* New graph input */}
            {creating && (
              <div className="flex items-center gap-1 p-2 bg-gray-100 dark:bg-zinc-800 rounded-xl border border-gray-200 dark:border-zinc-700">
                <input
                  autoFocus
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleCreateGraph(); if (e.key === 'Escape') setCreating(false); }}
                  placeholder="图谱名称..."
                  className="flex-1 bg-transparent text-sm text-gray-800 placeholder-gray-500 outline-none min-w-0"
                />
                <button onClick={handleCreateGraph} disabled={!newName.trim()} className="p-1 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition disabled:opacity-40">
                  <Check size={14} className="text-green-600" />
                </button>
                <button onClick={() => setCreating(false)} className="p-1 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition">
                  <X size={14} className="text-gray-500" />
                </button>
              </div>
            )}

            {loadingGraphs ? (
              <div className="text-center text-sm text-gray-500 py-8">加载中...</div>
            ) : graphs.length === 0 && !creating ? (
              <div className="text-center text-sm text-gray-500 py-8">
                <div className="text-2xl mb-2">🕸️</div>
                <p>暂无图谱</p>
                <p className="mt-1">点击 + 新建</p>
              </div>
            ) : (
              graphs.map(g => (
                <div
                  key={g.id}
                  onClick={() => setSelectedGraph(g)}
                  className={`group flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all ${
                    selectedGraph?.id === g.id
                      ? 'bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700'
                      : 'hover:bg-gray-100 dark:hover:bg-zinc-700 border border-transparent'
                  }`}
                >
                  {editingGraph?.id === g.id ? (
                    <input
                      autoFocus
                      value={editName}
                      onChange={e => setEditName(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') handleUpdateGraph(g); if (e.key === 'Escape') setEditingGraph(null); }}
                      onClick={e => e.stopPropagation()}
                      className="flex-1 bg-transparent text-sm text-gray-800 outline-none border-b border-gray-300 dark:border-zinc-600 min-w-0"
                    />
                  ) : (
                    <span className="flex-1 text-base text-gray-800 truncate font-medium">{g.name}</span>
                  )}
                  <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" onClick={e => e.stopPropagation()}>
                    <button
                      onClick={() => { setEditingGraph(g); setEditName(g.name); }}
                      className="p-1 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition"
                    >
                      <Edit2 size={12} className="text-gray-500" />
                    </button>
                    <button
                      onClick={() => handleDeleteGraph(g)}
                      className="p-1 hover:bg-red-100 rounded-lg transition"
                    >
                      <Trash2 size={12} className="text-gray-500 hover:text-red-600" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* ======== Right panel: graph content ======== */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!selectedGraph ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-6xl mb-4">🕸️</div>
              <p className="text-gray-600 font-medium">请选择或新建一个图谱</p>
              <p className="text-sm text-gray-500 mt-1">在左侧列表中选择图谱，或点击 + 创建新图谱</p>
            </div>
          </div>
        ) : (
          <>
            {/* Graph header */}
            <div className="px-6 pt-5 pb-4 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between shrink-0">
              <div>
                <h2 className="text-xl font-bold text-gray-800">{selectedGraph.name}</h2>
                <div className="flex items-center gap-4 mt-1">
                  <span className="text-sm text-gray-500">{nodes.length} 个实体</span>
                  <span className="text-sm text-gray-500">{edges.length} 条关系</span>
                  {allTypes.length > 0 && <span className="text-sm text-gray-500">{allTypes.length} 种类型</span>}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleExportCypher}
                  disabled={exporting || nodes.length === 0}
                  title="导出为 Neo4j Cypher 脚本"
                  className="px-4 py-2 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-2xl transition flex items-center gap-2 text-sm font-medium border border-gray-200 dark:border-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <Download size={15} />{exporting ? '导出中...' : '导出 Cypher'}
                </button>
                <button
                  onClick={() => setExtractModal(true)}
                  className="px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:shadow-lg transition flex items-center gap-2 text-sm font-medium"
                >
                  <Sparkles size={15} />从文本提取
                </button>
                <button
                  onClick={() => tab === 'edges' ? setEdgeModal(true) : setNodeModal({ open: true, editing: null })}
                  className="px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:shadow-lg transition flex items-center gap-2 text-sm font-medium"
                >
                  <Plus size={15} />{tab === 'edges' ? '添加边' : '添加节点'}
                </button>
              </div>
            </div>

            {/* Tabs + filter */}
            <div className="px-6 pt-4 pb-3 flex items-center gap-4 shrink-0">
              <div className="flex gap-1 bg-white dark:bg-zinc-900 rounded-xl p-1">
                {(['nodes', 'edges', 'graph'] as const).map(t => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                      tab === t ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900 shadow' : 'text-gray-600 hover:bg-gray-100 dark:hover:bg-zinc-700'
                    }`}
                  >
                    {t === 'nodes' ? '实体节点' : t === 'edges' ? '关系边' : '图谱视图'}
                  </button>
                ))}
              </div>

              {tab === 'nodes' && (
                <div className="flex items-center gap-2 flex-1">
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 flex-1 max-w-xs">
                    <Search size={13} className="text-gray-500 shrink-0" />
                    <input
                      value={search} onChange={e => setSearch(e.target.value)}
                      placeholder="搜索实体名称或描述..."
                      className="flex-1 bg-transparent text-sm text-gray-800 placeholder-gray-500 outline-none"
                    />
                    {search && <button onClick={() => setSearch('')}><X size={12} className="text-gray-500" /></button>}
                  </div>
                  <select
                    value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
                    className="px-3 py-1.5 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-xl text-sm text-gray-700 outline-none"
                  >
                    <option value="">全部类型</option>
                    {allTypes.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              )}
            </div>

            {/* Content */}
            {tab === 'graph' ? (
              loadingContent ? (
                <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">加载中...</div>
              ) : (
                <KGGraphView kgNodes={nodes} kgEdges={edges} />
              )
            ) : (
              <div className="flex-1 overflow-y-auto px-6 pb-6">
                {loadingContent ? (
                  <div className="text-center text-gray-500 py-16 text-sm">加载中...</div>
                ) : tab === 'nodes' ? (
                  filteredNodes.length === 0 ? (
                    <div className="text-center py-20">
                      <div className="text-5xl mb-4">🔷</div>
                      <p className="text-gray-600">暂无实体节点</p>
                      <p className="text-sm text-gray-500 mt-1">点击"添加节点"或"从文本提取"开始构建</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {filteredNodes.map(node => (
                        <div
                          key={node.id}
                          className="bg-white dark:bg-zinc-900 rounded-xl p-5 border border-gray-200 dark:border-zinc-700 group  hover:scale-[1.01] transition-all flex flex-col gap-2"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <h3 className="text-base font-semibold text-gray-800 truncate">{node.name}</h3>
                              {node.description && (
                                <p className="text-sm text-gray-500 mt-1 line-clamp-2">{node.description}</p>
                              )}
                            </div>
                            <span className={`ml-2 shrink-0 text-xs px-2.5 py-1 rounded-full border font-semibold ${typeColor(node.type)}`}>
                              {node.type}
                            </span>
                          </div>
                          <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity mt-1">
                            <button
                              onClick={() => setNodeModal({ open: true, editing: node })}
                              className="flex-1 py-2 text-sm bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-xl transition"
                            >
                              编辑
                            </button>
                            <button
                              onClick={() => handleNodeDelete(node)}
                              className="px-3 py-2 bg-gray-100 dark:bg-zinc-800 hover:bg-red-100 text-gray-700 hover:text-red-600 rounded-xl transition"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )
                ) : (
                  edges.length === 0 ? (
                    <div className="text-center py-20">
                      <div className="text-5xl mb-4">🔗</div>
                      <p className="text-gray-600">暂无关系边</p>
                      <p className="text-sm text-gray-500 mt-1">先添加至少两个节点，再建立它们之间的关系</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {edges.map(edge => {
                        const src = nodeMap[edge.source_node_id] ?? `#${edge.source_node_id}`;
                        const tgt = nodeMap[edge.target_node_id] ?? `#${edge.target_node_id}`;
                        return (
                          <div
                            key={edge.id}
                            className="bg-white dark:bg-zinc-900 rounded-2xl px-5 py-3 border border-gray-200 dark:border-zinc-700 flex items-center gap-3 group hover:bg-gray-100 dark:hover:bg-zinc-700 transition"
                          >
                            <span className="font-semibold text-gray-800 text-base">{src}</span>
                            <ChevronRight size={15} className="text-gray-600 dark:text-zinc-300 shrink-0" />
                            <span className="px-3 py-1 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 text-gray-600 dark:text-zinc-300 rounded-full text-sm font-semibold">
                              {edge.relation}
                            </span>
                            <ChevronRight size={15} className="text-gray-600 dark:text-zinc-300 shrink-0" />
                            <span className="font-semibold text-gray-800 text-base flex-1">{tgt}</span>
                            <button
                              onClick={() => handleEdgeDelete(edge)}
                              className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-100 text-gray-500 hover:text-red-600 rounded-lg transition"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Modals */}
      {nodeModal.open && (
        <NodeModal
          editing={nodeModal.editing}
          onClose={() => setNodeModal({ open: false, editing: null })}
          onSave={handleNodeSave}
        />
      )}
      {edgeModal && (
        <EdgeModal nodes={nodes} onClose={() => setEdgeModal(false)} onSave={handleEdgeSave} />
      )}
      {extractModal && selectedGraph && (
        <ExtractModal
          graphId={selectedGraph.id}
          agents={agents}
          onClose={() => setExtractModal(false)}
          onConfirm={handleExtractConfirm}
        />
      )}
    </div>
  );
};

export default KnowledgeGraphPage;
