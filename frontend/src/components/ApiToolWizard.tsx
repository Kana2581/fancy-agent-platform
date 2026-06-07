import React, { useState } from 'react';
import { Plus, Trash2, ChevronRight, ChevronLeft, Save, FlaskConical, Copy, Check } from 'lucide-react';
import ThemedSelect from './ThemedSelect';
import type { ApiToolCreate, ApiToolOut, ParamConfig, ResponseExtract } from '../api';
import { ApiToolsService } from '../api';
import { writeToClipboard } from '../utils/clipboard';

// ─── internal form shape ────────────────────────────────────────────────────

interface HeaderPair { key: string; value: string }

interface WizardForm {
  // step 1
  name: string;
  description: string;
  // step 2
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  param_location: 'query' | 'body' | 'path_and_query' | 'path_and_body';
  headers: HeaderPair[];
  fixed_params_json: string;
  // step 3
  tool_params: ParamConfig[];
  // step 4
  response_extract: ResponseExtract[];
  response_max_chars: number;
}

const emptyForm = (): WizardForm => ({
  name: '',
  description: '',
  url: '',
  method: 'GET',
  param_location: 'query',
  headers: [],
  fixed_params_json: '{}',
  tool_params: [],
  response_extract: [],
  response_max_chars: 2000,
});

function toolToForm(t: ApiToolOut): WizardForm {
  const headerPairs: HeaderPair[] = Object.entries(t.headers || {}).map(([key, value]) => ({ key, value }));
  return {
    name: t.name,
    description: t.description || '',
    url: t.url,
    method: t.method as WizardForm['method'],
    param_location: t.param_location as WizardForm['param_location'],
    headers: headerPairs,
    fixed_params_json: JSON.stringify(t.fixed_params || {}, null, 2),
    tool_params: (t.tool_params as ParamConfig[]) || [],
    response_extract: (t.response_extract as ResponseExtract[]) || [],
    response_max_chars: t.response_max_chars ?? 2000,
  };
}

function formToCreate(f: WizardForm): ApiToolCreate {
  const headers: Record<string, string> = {};
  for (const { key, value } of f.headers) {
    if (key.trim()) headers[key.trim()] = value;
  }
  let fixed_params: Record<string, unknown> = {};
  try { fixed_params = JSON.parse(f.fixed_params_json); } catch { /* ignore */ }

  return {
    name: f.name.trim(),
    description: f.description.trim() || undefined,
    url: f.url.trim(),
    method: f.method,
    param_location: f.param_location,
    headers,
    fixed_params,
    tool_params: f.tool_params,
    response_extract: f.response_extract,
    response_max_chars: f.response_max_chars,
  };
}

// ─── sub-components ──────────────────────────────────────────────────────────

const inputCls = 'w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none transition-all text-gray-800 placeholder-gray-500 text-sm';
const selectCls = 'w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 outline-none transition-all text-gray-800 dark:text-white text-sm';
const labelCls = 'block text-sm font-medium text-gray-800 mb-1.5';

function StepIndicator({ step }: { step: number }) {
  const steps = ['基本信息', 'API 配置', '参数配置', '响应配置'];
  return (
    <div className="flex items-center justify-between mb-8">
      {steps.map((label, i) => {
        const num = i + 1;
        const active = num === step;
        const done = num < step;
        return (
          <React.Fragment key={num}>
            <div className="flex flex-col items-center gap-1.5">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                active ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900 shadow-lg' :
                done  ? 'bg-green-400/80 text-white' :
                         'bg-gray-100 dark:bg-zinc-800 text-gray-500'
              }`}>
                {done ? <Check size={14} /> : num}
              </div>
              <span className={`text-xs ${active ? 'text-gray-800 font-medium' : 'text-gray-500'}`}>{label}</span>
            </div>
            {i < steps.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 rounded transition-all ${done ? 'bg-green-400/60' : 'bg-gray-100 dark:bg-zinc-800'}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Step 1 ──────────────────────────────────────────────────────────────────

function Step1({ form, onChange }: { form: WizardForm; onChange: (f: WizardForm) => void }) {
  return (
    <div className="space-y-5">
      <div>
        <label className={labelCls}>工具名称 <span className="text-red-400">*</span></label>
        <input
          className={inputCls}
          placeholder="例如：天气查询、股票行情..."
          value={form.name}
          onChange={e => onChange({ ...form, name: e.target.value })}
        />
        <p className="text-xs text-gray-500 mt-1">模型将用此名称识别并调用该工具</p>
      </div>
      <div>
        <label className={labelCls}>描述</label>
        <textarea
          className={inputCls + ' resize-none'}
          rows={4}
          placeholder="描述这个工具的功能，模型会依据此决定是否调用它..."
          value={form.description}
          onChange={e => onChange({ ...form, description: e.target.value })}
        />
      </div>
    </div>
  );
}

// ─── Step 2 ──────────────────────────────────────────────────────────────────

function Step2({ form, onChange }: { form: WizardForm; onChange: (f: WizardForm) => void }) {
  const [fixedError, setFixedError] = useState('');

  const addHeader = () => onChange({ ...form, headers: [...form.headers, { key: '', value: '' }] });
  const updateHeader = (i: number, field: 'key' | 'value', val: string) => {
    const h = [...form.headers];
    h[i] = { ...h[i], [field]: val };
    onChange({ ...form, headers: h });
  };
  const removeHeader = (i: number) => onChange({ ...form, headers: form.headers.filter((_, j) => j !== i) });

  const applyBearer = () => onChange({
    ...form,
    headers: [...form.headers.filter(h => h.key !== 'Authorization'), { key: 'Authorization', value: 'Bearer YOUR_TOKEN' }]
  });
  const applyApiKey = () => onChange({
    ...form,
    headers: [...form.headers.filter(h => h.key !== 'X-API-Key'), { key: 'X-API-Key', value: 'YOUR_KEY' }]
  });

  const paramLocationDesc: Record<string, string> = {
    query: 'URL 查询参数 (?key=val)',
    body: 'JSON 请求体',
    path_and_query: 'URL 路径变量 + 查询参数',
    path_and_body: 'URL 路径变量 + JSON 请求体',
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2">
          <label className={labelCls}>URL <span className="text-red-400">*</span></label>
          <input
            className={inputCls}
            placeholder="https://api.example.com/v1/{resource}"
            value={form.url}
            onChange={e => onChange({ ...form, url: e.target.value })}
          />
        </div>
        <div>
          <label className={labelCls}>方法</label>
          <ThemedSelect
            value={form.method}
            onChange={v => onChange({ ...form, method: v as WizardForm['method'] })}
            options={['GET','POST','PUT','DELETE','PATCH'].map(m => ({ value: m, label: m }))}
            className={selectCls}
          />
        </div>
      </div>

      <div>
        <label className={labelCls}>参数位置</label>
        <ThemedSelect
          value={form.param_location}
          onChange={v => onChange({ ...form, param_location: v as WizardForm['param_location'] })}
          options={Object.entries(paramLocationDesc).map(([k, v]) => ({ value: k, label: v }))}
          className={selectCls}
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className={labelCls + ' mb-0'}>请求头 (Headers)</label>
          <div className="flex gap-2">
            <button onClick={applyBearer} className="px-2.5 py-1 text-xs bg-purple-400/20 hover:bg-purple-400/30 text-gray-700 dark:text-zinc-300 rounded-lg transition-all border border-purple-300/30">Bearer Token</button>
            <button onClick={applyApiKey} className="px-2.5 py-1 text-xs bg-orange-400/20 hover:bg-orange-400/30 text-orange-800 rounded-lg transition-all border border-orange-300/30">API Key</button>
            <button onClick={addHeader} className="px-2.5 py-1 text-xs bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-lg transition-all border border-gray-200 dark:border-zinc-700 flex items-center gap-1"><Plus size={11} />添加</button>
          </div>
        </div>
        <div className="space-y-2">
          {form.headers.map((h, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input className={inputCls + ' flex-1'} placeholder="Header 名" value={h.key} onChange={e => updateHeader(i, 'key', e.target.value)} />
              <input className={inputCls + ' flex-1'} placeholder="值" value={h.value} onChange={e => updateHeader(i, 'value', e.target.value)} />
              <button onClick={() => removeHeader(i)} className="p-2 hover:bg-red-100/50 text-red-500 rounded-xl transition-all"><Trash2 size={15} /></button>
            </div>
          ))}
          {form.headers.length === 0 && <p className="text-xs text-gray-500 italic">暂无请求头</p>}
        </div>
      </div>

      <div>
        <label className={labelCls}>固定参数 (JSON)</label>
        <textarea
          className={`${inputCls} resize-none font-mono ${fixedError ? 'border-red-400' : ''}`}
          rows={4}
          value={form.fixed_params_json}
          onChange={e => {
            onChange({ ...form, fixed_params_json: e.target.value });
            try { JSON.parse(e.target.value); setFixedError(''); } catch { setFixedError('JSON 格式错误'); }
          }}
        />
        {fixedError && <p className="text-xs text-red-400 mt-1">{fixedError}</p>}
        <p className="text-xs text-gray-500 mt-1">每次调用都会包含这些参数，支持嵌套结构</p>
      </div>
    </div>
  );
}

// ─── Step 3 ──────────────────────────────────────────────────────────────────

function Step3({ form, onChange }: { form: WizardForm; onChange: (f: WizardForm) => void }) {
  const addParam = () => {
    const p: ParamConfig = { name: '', path: '', type: 'string', description: '', required: true, default: null };
    onChange({ ...form, tool_params: [...form.tool_params, p] });
  };

  const updateParam = (i: number, patch: Partial<ParamConfig>) => {
    const ps = [...form.tool_params];
    ps[i] = { ...ps[i], ...patch };
    onChange({ ...form, tool_params: ps });
  };

  const removeParam = (i: number) => onChange({ ...form, tool_params: form.tool_params.filter((_, j) => j !== i) });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">定义模型填写的参数字段</p>
        <button
          onClick={addParam}
          className="px-3 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm rounded-xl hover:shadow-lg transition-all flex items-center gap-1.5 font-medium"
        >
          <Plus size={15} />添加参数
        </button>
      </div>

      {form.tool_params.length === 0 && (
        <div className="text-center py-8 text-gray-500 text-sm">
          暂无参数，点击"添加参数"开始配置
        </div>
      )}

      {form.tool_params.map((p, i) => (
        <div key={i} className="p-4 bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-700 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">参数 #{i + 1}</span>
            <button onClick={() => removeParam(i)} className="p-1.5 hover:bg-red-100/50 text-red-500 rounded-lg transition-all"><Trash2 size={14} /></button>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>字段名 <span className="text-red-400">*</span></label>
              <input className={inputCls} placeholder="模型使用的名称（如 city）" value={p.name} onChange={e => updateParam(i, { name: e.target.value, path: p.path || e.target.value })} />
            </div>
            <div>
              <label className={labelCls}>请求路径</label>
              <input className={inputCls} placeholder="dot-path（如 filter.city）" value={p.path} onChange={e => updateParam(i, { path: e.target.value })} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelCls}>类型</label>
              <ThemedSelect
                value={p.type}
                onChange={v => updateParam(i, { type: v as ParamConfig['type'] })}
                options={[
                  { value: 'string', label: 'string' },
                  { value: 'integer', label: 'integer' },
                  { value: 'number', label: 'number' },
                  { value: 'boolean', label: 'boolean' },
                ]}
                className={selectCls}
              />
            </div>
            <div className="flex items-end pb-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input type="checkbox" checked={p.required} onChange={e => updateParam(i, { required: e.target.checked })} className="w-4 h-4 rounded text-gray-600 dark:text-zinc-300 focus:ring-gray-400 dark:focus:ring-zinc-500" />
                <span className="text-sm text-gray-700">必填</span>
              </label>
            </div>
          </div>
          <div>
            <label className={labelCls}>描述</label>
            <input className={inputCls} placeholder="告诉模型这个参数的含义..." value={p.description} onChange={e => updateParam(i, { description: e.target.value })} />
          </div>
          {!p.required && (
            <div>
              <label className={labelCls}>默认值</label>
              <input className={inputCls} placeholder="可选，不填则不传该参数" value={String(p.default ?? '')} onChange={e => updateParam(i, { default: e.target.value })} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Step 4 ──────────────────────────────────────────────────────────────────

function Step4({ form, onChange, toolId }: { form: WizardForm; onChange: (f: WizardForm) => void; toolId?: number }) {
  const [copied, setCopied] = useState(false);
  const [testParams, setTestParams] = useState<Record<string, string>>({});
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; result?: string; error?: string } | null>(null);

  const addExtract = () => onChange({ ...form, response_extract: [...form.response_extract, { path: '', alias: '' }] });
  const updateExtract = (i: number, patch: Partial<ResponseExtract>) => {
    const ex = [...form.response_extract];
    ex[i] = { ...ex[i], ...patch };
    onChange({ ...form, response_extract: ex });
  };
  const removeExtract = (i: number) => onChange({ ...form, response_extract: form.response_extract.filter((_, j) => j !== i) });

  const preview = JSON.stringify(formToCreate(form), null, 2);

  const handleCopy = () => {
    writeToClipboard(preview).catch(console.error);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTest = async () => {
    if (!toolId) return;
    setTestLoading(true);
    setTestResult(null);
    try {
      const params: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(testParams)) {
        if (v !== '') params[k] = v;
      }
      const res = await ApiToolsService.testApiToolApiV1ApiToolsToolIdTestPost(toolId, { params });
      setTestResult(res);
    } catch (e) {
      setTestResult({ success: false, error: String(e) });
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Response extract */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className={labelCls + ' mb-0'}>响应字段提取</label>
          <button onClick={addExtract} className="px-2.5 py-1 text-xs bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-lg border border-gray-200 dark:border-zinc-700 flex items-center gap-1"><Plus size={11} />添加</button>
        </div>
        <div className="space-y-2">
          {form.response_extract.map((ex, i) => (
            <div key={i} className="flex gap-2 items-center">
              <input className={inputCls + ' flex-1'} placeholder="提取路径（如 data.items[*]）" value={ex.path} onChange={e => updateExtract(i, { path: e.target.value })} />
              <input className={inputCls + ' flex-1'} placeholder="别名（如 items）" value={ex.alias} onChange={e => updateExtract(i, { alias: e.target.value })} />
              <button onClick={() => removeExtract(i)} className="p-2 hover:bg-red-100/50 text-red-500 rounded-xl"><Trash2 size={15} /></button>
            </div>
          ))}
          {form.response_extract.length === 0 && <p className="text-xs text-gray-500 italic">不配置则返回完整响应</p>}
        </div>
      </div>

      {/* Max chars */}
      <div>
        <label className={labelCls}>最大响应字符数</label>
        <input type="number" className={inputCls} value={form.response_max_chars} min={100} max={50000} onChange={e => onChange({ ...form, response_max_chars: parseInt(e.target.value) || 2000 })} />
      </div>

      {/* JSON preview */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className={labelCls + ' mb-0'}>完整配置预览</label>
          <button onClick={handleCopy} className="px-2.5 py-1 text-xs bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-lg border border-gray-200 dark:border-zinc-700 flex items-center gap-1">
            {copied ? <><Check size={11} className="text-green-500" />已复制</> : <><Copy size={11} />复制</>}
          </button>
        </div>
        <pre className="p-4 bg-black/30 rounded-2xl text-xs text-green-300 overflow-auto max-h-48 border border-gray-100 dark:border-zinc-800/50 font-mono">
          {preview}
        </pre>
      </div>

      {/* Test panel */}
      <div className="border-t border-gray-200 dark:border-zinc-800 pt-4">
        <div className="flex items-center gap-2 mb-3">
          <FlaskConical size={16} className="text-gray-600 dark:text-zinc-400" />
          <span className="text-sm font-medium text-gray-800">测试面板</span>
          {!toolId && <span className="text-xs text-gray-500">（保存后可测试）</span>}
        </div>
        {toolId ? (
          <div className="space-y-3">
            {form.tool_params.length > 0 ? (
              <div className="grid grid-cols-2 gap-2">
                {form.tool_params.map(p => (
                  <div key={p.name}>
                    <label className="text-xs text-gray-600 mb-1 block">{p.name} <span className="text-gray-400">({p.type})</span></label>
                    <input
                      className={inputCls}
                      placeholder={p.required ? '必填' : '可选'}
                      value={testParams[p.name] ?? ''}
                      onChange={e => setTestParams(prev => ({ ...prev, [p.name]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-500 italic">该工具无参数</p>
            )}
            <button
              onClick={handleTest}
              disabled={testLoading}
              className="px-4 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm rounded-xl hover:shadow-lg transition-all flex items-center gap-2 disabled:opacity-50"
            >
              <FlaskConical size={15} />
              {testLoading ? '请求中...' : '发送测试请求'}
            </button>
            {testResult && (
              <div className={`rounded-xl border overflow-hidden ${testResult.success ? 'border-emerald-500/40' : 'border-red-500/40'}`}>
                <div className={`px-3 py-1.5 text-xs font-medium ${testResult.success ? 'bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-300' : 'bg-red-500/30 text-red-900'}`}>
                  {testResult.success ? '✓ 请求成功' : '✗ 请求失败'}
                </div>
                <pre className={`p-3 text-xs font-mono overflow-auto max-h-40 text-gray-800 ${testResult.success ? 'bg-emerald-400/10' : 'bg-red-400/10'}`}>
                  {testResult.success ? testResult.result : `错误: ${testResult.error}`}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-gray-500 bg-gray-50 dark:bg-zinc-900 rounded-xl p-3 border border-gray-200 dark:border-zinc-800">保存工具后，在编辑界面即可使用测试功能</p>
        )}
      </div>
    </div>
  );
}

// ─── Main wizard ─────────────────────────────────────────────────────────────

interface ApiToolWizardProps {
  initialTool?: ApiToolOut;
  onSave: (data: ApiToolCreate) => Promise<void>;
  onCancel: () => void;
}

const ApiToolWizard: React.FC<ApiToolWizardProps> = ({ initialTool, onSave, onCancel }) => {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [form, setForm] = useState<WizardForm>(initialTool ? toolToForm(initialTool) : emptyForm());
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const validate = (s: number): string[] => {
    const errs: string[] = [];
    if (s === 1) {
      if (!form.name.trim()) errs.push('工具名称不能为空');
    }
    if (s === 2) {
      if (!form.url.trim()) errs.push('URL 不能为空');
      try { JSON.parse(form.fixed_params_json); } catch { errs.push('固定参数 JSON 格式错误'); }
    }
    if (s === 3) {
      for (const p of form.tool_params) {
        if (!p.name.trim()) errs.push(`参数缺少字段名`);
        if (!p.path.trim()) errs.push(`参数 "${p.name}" 缺少请求路径`);
      }
    }
    return errs;
  };

  const next = () => {
    const errs = validate(step);
    if (errs.length) { setErrors(errs); return; }
    setErrors([]);
    setStep(prev => (prev < 4 ? (prev + 1) as typeof step : prev));
  };

  const back = () => {
    setErrors([]);
    setStep(prev => (prev > 1 ? (prev - 1) as typeof step : prev));
  };

  const handleSave = async () => {
    const errs = [...validate(1), ...validate(2), ...validate(3)];
    if (errs.length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await onSave(formToCreate(form));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <StepIndicator step={step} />

      {errors.length > 0 && (
        <div className="mb-4 p-3 bg-red-400/10 border border-red-400/30 rounded-xl">
          {errors.map((e, i) => <p key={i} className="text-xs text-red-600">{e}</p>)}
        </div>
      )}

      <div className="min-h-[320px]">
        {step === 1 && <Step1 form={form} onChange={setForm} />}
        {step === 2 && <Step2 form={form} onChange={setForm} />}
        {step === 3 && <Step3 form={form} onChange={setForm} />}
        {step === 4 && <Step4 form={form} onChange={setForm} toolId={initialTool?.id} />}
      </div>

      <div className="flex justify-between mt-8 pt-4 border-t border-gray-200 dark:border-zinc-800">
        <button
          onClick={step === 1 ? onCancel : back}
          className="px-5 py-2.5 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-2xl transition-all flex items-center gap-2"
        >
          <ChevronLeft size={16} />
          {step === 1 ? '取消' : '上一步'}
        </button>

        {step < 4 ? (
          <button
            onClick={next}
            className="px-5 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:shadow-lg transition-all flex items-center gap-2 font-medium"
          >
            下一步 <ChevronRight size={16} />
          </button>
        ) : (
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:shadow-lg transition-all flex items-center gap-2 font-medium disabled:opacity-50"
          >
            <Save size={16} />
            {saving ? '保存中...' : '保存工具'}
          </button>
        )}
      </div>
    </div>
  );
};

export default ApiToolWizard;
