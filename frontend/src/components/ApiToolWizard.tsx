import React, { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, Copy, FlaskConical, Plus, Save, Trash2, Check } from 'lucide-react'
import toast from 'react-hot-toast'
import type { ApiToolCreate, ApiToolOut, TemplateVariable } from '../api'
import { ApiToolsService } from '../api'
import ThemedSelect from './ThemedSelect'
import { writeToClipboard } from '../utils/clipboard'

interface HeaderPair { key: string; value: string }
interface WizardForm {
  name: string
  description: string
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  param_location: 'query' | 'body' | 'path_and_query' | 'path_and_body'
  headers: HeaderPair[]
  request_template_json: string
  tool_params: TemplateVariable[]
  response_template: string
  response_max_chars: number
}

const emptyForm = (): WizardForm => ({
  name: '', description: '', url: '', method: 'GET', param_location: 'query', headers: [],
  request_template_json: '{}', tool_params: [], response_template: '', response_max_chars: 2000,
})

function toolToForm(tool: ApiToolOut): WizardForm {
  return {
    name: tool.name,
    description: tool.description || '',
    url: tool.url,
    method: tool.method as WizardForm['method'],
    param_location: tool.param_location as WizardForm['param_location'],
    headers: Object.entries(tool.headers || {}).map(([key, value]) => ({ key, value })),
    request_template_json: JSON.stringify(tool.request_template || {}, null, 2),
    tool_params: tool.tool_params || [],
    response_template: tool.response_template || '',
    response_max_chars: tool.response_max_chars ?? 2000,
  }
}

const inputCls = 'w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 outline-none transition-all text-gray-800 dark:text-white placeholder-gray-500 text-sm'
const selectCls = 'w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl outline-none transition-all text-gray-800 dark:text-white text-sm'
const labelCls = 'block text-sm font-medium text-gray-800 dark:text-zinc-200 mb-1.5'

const VARIABLE_RE = /{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}/g

function collectVariables(value: unknown, result: string[] = []): string[] {
  if (typeof value === 'string') {
    for (const match of value.matchAll(VARIABLE_RE)) if (!result.includes(match[1])) result.push(match[1])
  } else if (Array.isArray(value)) {
    value.forEach((item) => collectVariables(item, result))
  } else if (value && typeof value === 'object') {
    Object.entries(value).forEach(([key, item]) => {
      collectVariables(key, result)
      collectVariables(item, result)
    })
  }
  return result
}

function scanFormVariables(form: WizardForm): string[] {
  const names = collectVariables(form.url)
  form.headers.forEach((header) => {
    collectVariables(header.key, names)
    collectVariables(header.value, names)
  })
  try { collectVariables(JSON.parse(form.request_template_json), names) } catch { /* validation reports this */ }
  return names
}

function syncVariables(form: WizardForm): WizardForm {
  const names = scanFormVariables(form)
  const old = new Map(form.tool_params.map((item) => [item.name, item]))
  return {
    ...form,
    tool_params: names.map((name) => old.get(name) || {
      name, type: 'string', description: '', required: true, default: null,
    }),
  }
}

function coerceDefault(type: TemplateVariable['type'], raw: unknown): unknown {
  if (raw === null || raw === undefined || raw === '') return null
  if (typeof raw !== 'string') return raw
  if (type === 'integer') return Number.isNaN(parseInt(raw, 10)) ? null : parseInt(raw, 10)
  if (type === 'number') return Number.isNaN(parseFloat(raw)) ? null : parseFloat(raw)
  if (type === 'boolean') return raw.trim().toLowerCase() === 'true'
  return raw
}

function displayDefault(value: unknown): string {
  if (value === null || value === undefined) return ''
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function formToCreate(form: WizardForm): ApiToolCreate {
  const requestTemplate = JSON.parse(form.request_template_json)
  const headers: Record<string, string> = {}
  form.headers.forEach(({ key, value }) => { if (key.trim()) headers[key.trim()] = value })
  return {
    name: form.name.trim(), description: form.description.trim() || undefined, url: form.url.trim(),
    method: form.method, param_location: form.param_location, headers,
    request_template: requestTemplate,
    tool_params: form.tool_params.map((item) => ({
      ...item, description: item.description || '', default: item.required ? null : coerceDefault(item.type, item.default),
    })),
    response_template: form.response_template.trim() || null,
    response_max_chars: form.response_max_chars,
  }
}

function StepIndicator({ step, onJump }: { step: number; onJump: (step: number) => void }) {
  const steps = ['基本信息', '请求模板', '变量参数', '响应模板']
  return <div className="flex items-center justify-between mb-8">
    {steps.map((label, index) => {
      const number = index + 1
      return <React.Fragment key={label}>
        <button type="button" onClick={() => onJump(number)} className="flex flex-col items-center gap-1.5">
          <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${number === step ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900' : number < step ? 'bg-green-400 text-white' : 'bg-gray-100 dark:bg-zinc-800 text-gray-500'}`}>
            {number < step ? <Check size={14} /> : number}
          </span>
          <span className={`text-xs ${number === step ? 'text-gray-800 dark:text-white font-medium' : 'text-gray-500'}`}>{label}</span>
        </button>
        {index < steps.length - 1 && <div className={`flex-1 h-0.5 mx-2 ${number < step ? 'bg-green-400/60' : 'bg-gray-100 dark:bg-zinc-800'}`} />}
      </React.Fragment>
    })}
  </div>
}

function Step1({ form, onChange }: { form: WizardForm; onChange: (form: WizardForm) => void }) {
  return <div className="space-y-5">
    <div><label className={labelCls}>工具名称 <span className="text-red-400">*</span></label><input className={inputCls} placeholder="例如：天气查询" value={form.name} onChange={(e) => onChange({ ...form, name: e.target.value })} /><p className="text-xs text-gray-500 mt-1">模型会根据名称和描述决定是否调用工具</p></div>
    <div><label className={labelCls}>描述</label><textarea className={`${inputCls} resize-none`} rows={4} placeholder="描述这个 API 的用途、适用场景和返回内容" value={form.description} onChange={(e) => onChange({ ...form, description: e.target.value })} /></div>
  </div>
}

function Step2({ form, onChange }: { form: WizardForm; onChange: (form: WizardForm) => void }) {
  const update = (patch: Partial<WizardForm>) => onChange(syncVariables({ ...form, ...patch }))
  const updateHeader = (index: number, patch: Partial<HeaderPair>) => update({ headers: form.headers.map((item, i) => i === index ? { ...item, ...patch } : item) })
  return <div className="space-y-5">
    <div className="grid grid-cols-3 gap-3"><div className="col-span-2"><label className={labelCls}>URL 模板 <span className="text-red-400">*</span></label><input className={inputCls} placeholder="https://api.example.com/weather?city={{city}}" value={form.url} onChange={(e) => update({ url: e.target.value })} /></div><div><label className={labelCls}>方法</label><ThemedSelect value={form.method} onChange={(value) => update({ method: value as WizardForm['method'] })} options={['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((value) => ({ value, label: value }))} className={selectCls} /></div></div>
    <div><label className={labelCls}>参数位置</label><ThemedSelect value={form.param_location} onChange={(value) => update({ param_location: value as WizardForm['param_location'] })} options={[['query', 'Query 参数模板'], ['body', 'JSON Body 模板'], ['path_and_query', 'URL 路径 + Query'], ['path_and_body', 'URL 路径 + JSON Body']].map(([value, label]) => ({ value, label }))} className={selectCls} /></div>
    <div><div className="flex justify-between items-center mb-2"><label className={`${labelCls} mb-0`}>请求头模板</label><button type="button" onClick={() => update({ headers: [...form.headers, { key: '', value: '' }] })} className="px-2.5 py-1 text-xs bg-gray-100 dark:bg-zinc-800 rounded-lg flex items-center gap-1"><Plus size={11} />添加</button></div><div className="space-y-2">{form.headers.map((header, index) => <div key={index} className="flex gap-2"><input className={inputCls} placeholder="Header 名" value={header.key} onChange={(e) => updateHeader(index, { key: e.target.value })} /><input className={inputCls} placeholder="例如 Bearer {{token}}" value={header.value} onChange={(e) => updateHeader(index, { value: e.target.value })} /><button type="button" onClick={() => update({ headers: form.headers.filter((_, i) => i !== index) })} className="p-2 text-red-500"><Trash2 size={15} /></button></div>)}</div></div>
     <div><label className={labelCls}>Query / Body 模板（JSON）</label><textarea className={`${inputCls} resize-none font-mono ${form.request_template_json.trim() ? '' : 'border-red-400'}`} rows={8} value={form.request_template_json} onChange={(e) => update({ request_template_json: e.target.value })} /><p className="text-xs text-gray-500 mt-1">直接在值中写变量占位符，例如 city、page；完整占位符会按变量类型发送。</p></div>
  </div>
}

function Step3({ form, onChange }: { form: WizardForm; onChange: (form: WizardForm) => void }) {
  const updateParam = (index: number, patch: Partial<TemplateVariable>) => onChange({ ...form, tool_params: form.tool_params.map((item, i) => i === index ? { ...item, ...patch } : item) })
  return <div className="space-y-4">
    <div className="flex items-center justify-between"><div><p className="text-sm text-gray-700 dark:text-zinc-300">以下参数由 URL、Header 和 JSON 模板自动扫描生成。</p><p className="text-xs text-gray-500 mt-1">同名变量可在多个位置复用，删除模板中的变量后会自动移除。</p></div><span className="text-xs px-2.5 py-1 rounded-full bg-gray-100 dark:bg-zinc-800 text-gray-500">{form.tool_params.length} 个变量</span></div>
     {form.tool_params.length === 0 ? <div className="text-center py-12 text-gray-500 text-sm border border-dashed border-gray-300 dark:border-zinc-700 rounded-2xl">还没有发现变量，请回到“请求模板”填写变量占位符</div> : form.tool_params.map((param, index) => <div key={param.name} className="p-4 bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-700 space-y-3"><div className="flex items-center justify-between"><code className="text-sm text-purple-600 dark:text-purple-300">{'{{'}{param.name}{'}}'}</code><label className="flex items-center gap-2 text-sm text-gray-700 dark:text-zinc-300"><input type="checkbox" checked={param.required !== false} onChange={(e) => updateParam(index, { required: e.target.checked })} />必填</label></div><div className="grid grid-cols-2 gap-3"><div><label className={labelCls}>类型</label><ThemedSelect value={param.type} onChange={(value) => updateParam(index, { type: value as TemplateVariable['type'] })} options={['string', 'integer', 'number', 'boolean'].map((value) => ({ value, label: value }))} className={selectCls} /></div>{param.required === false && <div><label className={labelCls}>默认值</label><input className={inputCls} value={displayDefault(param.default)} placeholder="可选" onChange={(e) => updateParam(index, { default: e.target.value })} /></div>}</div><div><label className={labelCls}>描述</label><input className={inputCls} placeholder="告诉模型这个参数的含义" value={param.description || ''} onChange={(e) => updateParam(index, { description: e.target.value })} /></div></div>)}
  </div>
}

function Step4({ form, onChange, toolId }: { form: WizardForm; onChange: (form: WizardForm) => void; toolId?: number }) {
  const [copied, setCopied] = useState(false)
  const [testParams, setTestParams] = useState<Record<string, string>>({})
  const [testResult, setTestResult] = useState<{ success: boolean; result?: string; error?: string } | null>(null)
  const [testLoading, setTestLoading] = useState(false)
  const preview = useMemo(() => { try { return JSON.stringify(formToCreate(form), null, 2) } catch { return '请求模板 JSON 格式错误' } }, [form])
  const copy = () => { void writeToClipboard(preview); setCopied(true); setTimeout(() => setCopied(false), 1500) }
  const test = async () => {
    if (!toolId) return
    setTestLoading(true); setTestResult(null)
    try { const result = await ApiToolsService.testApiToolApiV1ApiToolsToolIdTestPost(toolId, { params: testParams }); setTestResult(result) } catch (error) { setTestResult({ success: false, error: String(error) }) } finally { setTestLoading(false) }
  }
  return <div className="space-y-5"><div><label className={labelCls}>响应模板</label><textarea className={`${inputCls} resize-none font-mono`} rows={5} placeholder={'例如：天气：{{data.city}}，温度：{{data.temperature}}'} value={form.response_template} onChange={(e) => onChange({ ...form, response_template: e.target.value })} /><p className="text-xs text-gray-500 mt-1">支持 dot-path、数组索引和 data.items[*] 路径；不填则返回完整 JSON。</p></div><div><label className={labelCls}>最大响应字符数</label><input type="number" min={100} max={50000} className={inputCls} value={form.response_max_chars} onChange={(e) => onChange({ ...form, response_max_chars: parseInt(e.target.value, 10) || 2000 })} /></div><div><div className="flex items-center justify-between mb-2"><label className={labelCls}>完整配置预览</label><button type="button" onClick={copy} className="px-2.5 py-1 text-xs bg-gray-100 dark:bg-zinc-800 rounded-lg flex items-center gap-1">{copied ? <Check size={11} /> : <Copy size={11} />}{copied ? '已复制' : '复制'}</button></div><pre className="p-4 bg-black/30 rounded-2xl text-xs text-green-300 overflow-auto max-h-48 font-mono">{preview}</pre></div><div className="border-t border-gray-200 dark:border-zinc-800 pt-4"><div className="flex items-center gap-2 mb-3"><FlaskConical size={16} /><span className="text-sm font-medium">测试面板</span>{!toolId && <span className="text-xs text-gray-500">保存后可测试</span>}</div>{toolId ? <div className="space-y-3">{form.tool_params.length > 0 && <div className="grid grid-cols-2 gap-2">{form.tool_params.map((param) => <div key={param.name}><label className="text-xs text-gray-600 dark:text-zinc-400 mb-1 block">{param.name} {param.required !== false && <span className="text-red-400">*</span>}</label><input className={inputCls} value={testParams[param.name] || ''} onChange={(e) => setTestParams({ ...testParams, [param.name]: e.target.value })} /></div>)}</div>}<button type="button" onClick={() => void test()} disabled={testLoading} className="px-4 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm rounded-xl disabled:opacity-50 flex items-center gap-2"><FlaskConical size={15} />{testLoading ? '请求中...' : '发送测试请求'}</button>{testResult && <pre className={`p-3 text-xs font-mono overflow-auto max-h-40 rounded-xl ${testResult.success ? 'bg-emerald-400/10' : 'bg-red-400/10'}`}>{testResult.success ? testResult.result : `错误：${testResult.error}`}</pre>}</div> : <p className="text-xs text-gray-500">保存工具后，在编辑界面测试请求。</p>}</div></div>
}

interface ApiToolWizardProps { initialTool?: ApiToolOut; onSave: (data: ApiToolCreate) => Promise<void>; onCancel: () => void }

const ApiToolWizard: React.FC<ApiToolWizardProps> = ({ initialTool, onSave, onCancel }) => {
  const [step, setStep] = useState(1)
  const [form, setForm] = useState<WizardForm>(() => initialTool ? toolToForm(initialTool) : emptyForm())
  const [errors, setErrors] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const validate = (currentStep: number) => {
    const errors: string[] = []
    if (currentStep === 1 && !form.name.trim()) errors.push('工具名称不能为空')
    if (currentStep === 2) { if (!form.url.trim()) errors.push('URL 不能为空'); try { JSON.parse(form.request_template_json) } catch { errors.push('请求模板 JSON 格式错误') } }
    if (currentStep === 3 && scanFormVariables(form).some((name) => !form.tool_params.find((item) => item.name === name))) errors.push('存在未配置的模板变量')
    return errors
  }
  const next = () => { const found = validate(step); if (found.length) { setErrors(found); return }; setErrors([]); setStep(Math.min(4, step + 1)) }
  const save = async () => { const found = [1, 2, 3].flatMap(validate); if (found.length) { setErrors(found); return }; setSaving(true); try { await onSave(formToCreate(form)) } catch (error) { toast.error(String(error)) } finally { setSaving(false) } }
  return <div><StepIndicator step={step} onJump={(value) => { setErrors([]); setStep(value) }} />{errors.length > 0 && <div className="mb-4 p-3 bg-red-400/10 border border-red-400/30 rounded-xl">{errors.map((error) => <p key={error} className="text-xs text-red-600">{error}</p>)}</div>}<div className="min-h-[320px]">{step === 1 && <Step1 form={form} onChange={setForm} />}{step === 2 && <Step2 form={form} onChange={setForm} />}{step === 3 && <Step3 form={form} onChange={setForm} />}{step === 4 && <Step4 form={form} onChange={setForm} toolId={initialTool?.id} />}</div><div className="flex justify-between mt-8 pt-4 border-t border-gray-200 dark:border-zinc-800"><button type="button" onClick={step === 1 ? onCancel : () => setStep(step - 1)} className="px-5 py-2.5 bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-200 rounded-2xl flex items-center gap-2"><ChevronLeft size={16} />{step === 1 ? '取消' : '上一步'}</button>{step < 4 ? <button type="button" onClick={next} className="px-5 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl flex items-center gap-2">下一步<ChevronRight size={16} /></button> : <button type="button" onClick={() => void save()} disabled={saving} className="px-5 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl flex items-center gap-2 disabled:opacity-50"><Save size={16} />{saving ? '保存中...' : '保存工具'}</button>}</div></div>
}

export default ApiToolWizard
