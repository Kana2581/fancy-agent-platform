import React, { useState } from 'react';
import { ChevronRight, ChevronLeft, Loader2, Image } from 'lucide-react';
import ThemedSelect from './ThemedSelect';
import type { ImageToolCreate, ImageToolOut } from '../api';
import { ImageToolsService } from '../api';

interface Props {
  initialTool?: ImageToolOut;
  onSave: (data: ImageToolCreate) => Promise<void>;
  onCancel: () => void;
}

const OPENAI_SIZES_DALLE3 = ['1024x1024', '1024x1792', '1792x1024'];
const OPENAI_SIZES_DALLE2 = ['256x256', '512x512', '1024x1024'];
const OPENAI_QUALITIES = ['standard', 'hd'];
const OPENAI_STYLES = ['vivid', 'natural'];
const IMG2IMG_PROVIDERS = new Set(['openai', 'stability']);

const ImageToolWizard: React.FC<Props> = ({ initialTool, onSave, onCancel }) => {
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [testPrompt, setTestPrompt] = useState('');
  const [testImage, setTestImage] = useState<string | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);
  const [savedToolId, setSavedToolId] = useState<number | null>(initialTool?.id ?? null);

  const [form, setForm] = useState<ImageToolCreate>({
    name: initialTool?.name ?? '',
    description: initialTool?.description ?? '',
    provider: initialTool?.provider ?? 'openai',
    api_key: initialTool?.api_key ?? '',
    base_url: initialTool?.base_url ?? '',
    model: initialTool?.model ?? '',
    default_size: initialTool?.default_size ?? '1024x1024',
    default_quality: initialTool?.default_quality ?? 'standard',
    default_style: initialTool?.default_style ?? 'vivid',
    extra_params: initialTool?.extra_params ?? {},
    support_img2img: initialTool?.support_img2img ?? false,
  });

  const set = (field: keyof ImageToolCreate, value: unknown) =>
    setForm(prev => ({ ...prev, [field]: value }));

  const setExtra = (key: string, value: unknown) =>
    setForm(prev => ({ ...prev, extra_params: { ...(prev.extra_params ?? {}), [key]: value } }));

  const PROVIDER_LABELS: Record<string, string> = { openai: 'DALL-E', stability: 'Stability AI', siliconflow: '硅基流动', aliyun: '阿里云（千问）' };

  const handleNext = async () => {
    setSaving(true);
    // Auto-generate name from provider if not set
    const nameToUse = form.name || PROVIDER_LABELS[form.provider] || form.provider;
    const formToSave = { ...form, name: nameToUse };
    if (!form.name) setForm(prev => ({ ...prev, name: nameToUse }));
    try {
      if (savedToolId) {
        await ImageToolsService.updateImageTool(savedToolId, formToSave);
      } else {
        const created = await ImageToolsService.createImageTool(formToSave);
        setSavedToolId(created.id);
      }
      setStep(2);
    } catch (e: unknown) {
      alert('保存失败: ' + String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (savedToolId) {
        await ImageToolsService.updateImageTool(savedToolId, form);
      }
      await onSave(form);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!testPrompt.trim() || !savedToolId) return;
    setTestLoading(true);
    setTestError(null);
    setTestImage(null);
    try {
      const res = await ImageToolsService.generateImage(savedToolId, { prompt: testPrompt });
      setTestImage(res.image_url);
    } catch (e: unknown) {
      setTestError(String(e));
    } finally {
      setTestLoading(false);
    }
  };

  const PROVIDER_DEFAULT_SIZES: Record<string, string> = {
    openai: '1024x1024',
    stability: '1024x1024',
    siliconflow: '1024x1024',
    aliyun: '2048*2048',
  };

  // ✅ 切换 provider 时同步清空模型选择，并设置默认尺寸
  const handleProviderChange = (provider: string) => {
    set('provider', provider);
    set('model', '');
    set('default_size', PROVIDER_DEFAULT_SIZES[provider] ?? '1024x1024');
    if (!IMG2IMG_PROVIDERS.has(provider)) {
      set('support_img2img', false);
    }
  };

  const SILICONFLOW_SIZES = ['512x512', '768x768', '1024x1024', '1024x576', '576x1024'];
  const ALIYUN_SIZES = ['2048*2048', '2688*1536', '1536*2688', '2368*1728', '1728*2368'];

  const sizes = form.provider === 'openai'
    ? (form.model === 'dall-e-2' ? OPENAI_SIZES_DALLE2 : OPENAI_SIZES_DALLE3)
    : form.provider === 'siliconflow'
    ? SILICONFLOW_SIZES
    : form.provider === 'aliyun'
    ? ALIYUN_SIZES
    : ['512x512', '768x768', '1024x1024'];

  // ✅ 步骤二的保存需要模型已选择
  const canProceedStep2 = !!form.model;

  const inputClass = 'w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-xl text-gray-800 placeholder-gray-500 outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50';
  const selectClass = 'w-full px-4 py-2.5 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-xl text-gray-800 outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50';
  const labelClass = 'block text-sm font-medium text-gray-700 mb-1';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-2">
        {[1, 2].map(s => (
          <div key={s} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
              s === step ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
              : s < step ? 'bg-green-400/60 text-white' : 'bg-gray-100 dark:bg-zinc-800 text-gray-600'
            }`}>{s}</div>
            {s < 2 && <div className="w-8 h-0.5 bg-gray-100 dark:bg-zinc-800" />}
          </div>
        ))}
        <span className="ml-2 text-sm text-gray-600">{step === 1 ? '基本信息' : '模型参数 & 测试'}</span>
      </div>

      {step === 1 && (
        <div className="space-y-4">
          <div>
            <label className={labelClass}>描述（可选）</label>
            <input type="text" value={form.description ?? ''} onChange={e => set('description', e.target.value)}
              placeholder="可选描述" className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Provider *</label>
            {/* ✅ 使用新的 handleProviderChange */}
            <ThemedSelect
              value={form.provider}
              onChange={v => handleProviderChange(v)}
              options={[
                { value: 'openai', label: 'OpenAI (DALL-E)' },
                { value: 'stability', label: 'Stability AI' },
                { value: 'siliconflow', label: '硅基流动 (SiliconFlow)' },
                { value: 'aliyun', label: '阿里云百炼（Qwen-Image）' },
              ]}
              className={selectClass}
            />
          </div>
          <div>
            <label className={labelClass}>API Key *</label>
            <input type="password" value={form.api_key} onChange={e => set('api_key', e.target.value)}
              placeholder="sk-..." className={inputClass} />
          </div>
          <div>
            <label className={labelClass}>Base URL（可选，代理端点）</label>
            <input type="text" value={form.base_url ?? ''} onChange={e => set('base_url', e.target.value || null)}
              placeholder="https://..." className={inputClass} />
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          {form.provider === 'openai' && (
            <>
              <div>
                <label className={labelClass}>模型 *</label>
                <input
                  type="text"
                  value={form.model ?? ''}
                  onChange={e => {
                    set('model', e.target.value);
                    set('default_size', '1024x1024');
                  }}
                  placeholder="例如：dall-e-3、dall-e-2"
                  className={inputClass}
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={labelClass}>尺寸</label>
                  <ThemedSelect value={form.default_size ?? '1024x1024'} onChange={v => set('default_size', v)} options={sizes.map(s => ({ value: s, label: s }))} className={selectClass} />
                </div>
                <div>
                  <label className={labelClass}>质量</label>
                  <ThemedSelect value={form.default_quality ?? 'standard'} onChange={v => set('default_quality', v)} options={OPENAI_QUALITIES.map(q => ({ value: q, label: q }))} className={selectClass} disabled={form.model === 'dall-e-2'} />
                </div>
                <div>
                  <label className={labelClass}>风格</label>
                  <ThemedSelect value={form.default_style ?? 'vivid'} onChange={v => set('default_style', v)} options={OPENAI_STYLES.map(s => ({ value: s, label: s }))} className={selectClass} disabled={form.model === 'dall-e-2'} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="img2img"
                  checked={form.support_img2img}
                  onChange={e => set('support_img2img', e.target.checked)}
                  className="rounded"
                />
                <label htmlFor="img2img" className="text-sm text-gray-700">
                  支持图生图（img2img）
                </label>
              </div>
            </>
          )}

          {form.provider === 'stability' && (
            <>
              <div>
                <label className={labelClass}>Engine ID *</label>
                <input
                  type="text"
                  value={form.model ?? ''}
                  onChange={e => set('model', e.target.value)}
                  placeholder="例如：stable-diffusion-xl-1024-v1-0"
                  className={inputClass}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Steps（默认 30）</label>
                  <input type="number" value={(form.extra_params as Record<string, number>)?.steps ?? 30}
                    onChange={e => setExtra('steps', Number(e.target.value))} min={10} max={150} className={inputClass} />
                </div>
                <div>
                  <label className={labelClass}>CFG Scale（默认 7）</label>
                  <input type="number" value={(form.extra_params as Record<string, number>)?.cfg_scale ?? 7}
                    onChange={e => setExtra('cfg_scale', Number(e.target.value))} min={1} max={35} step={0.5} className={inputClass} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="img2img" checked={form.support_img2img}
                  onChange={e => set('support_img2img', e.target.checked)} className="rounded" />
                <label htmlFor="img2img" className="text-sm text-gray-700">支持图生图（img2img）</label>
              </div>
            </>
          )}

          {form.provider === 'siliconflow' && (
            <>
              <div>
                <label className={labelClass}>模型 *</label>
                <input
                  type="text"
                  value={form.model ?? ''}
                  onChange={e => set('model', e.target.value)}
                  placeholder="例如：stabilityai/stable-diffusion-xl-base-1.0"
                  className={inputClass}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>尺寸</label>
                  <ThemedSelect value={form.default_size ?? '1024x1024'} onChange={v => set('default_size', v)} options={sizes.map(s => ({ value: s, label: s }))} className={selectClass} />
                </div>
                <div>
                  <label className={labelClass}>推理步数（默认 20）</label>
                  <input type="number" value={(form.extra_params as Record<string, number>)?.num_inference_steps ?? 20}
                    onChange={e => setExtra('num_inference_steps', Number(e.target.value))} min={1} max={100} className={inputClass} />
                </div>
              </div>
              <div>
                <label className={labelClass}>Guidance Scale（默认 7.5）</label>
                <input type="number" value={(form.extra_params as Record<string, number>)?.guidance_scale ?? 7.5}
                  onChange={e => setExtra('guidance_scale', Number(e.target.value))} min={1} max={20} step={0.5} className={inputClass} />
              </div>
            </>
          )}

          {form.provider === 'aliyun' && (
            <>
              <div>
                <label className={labelClass}>模型 *</label>
                <input
                  type="text"
                  value={form.model ?? ''}
                  onChange={e => set('model', e.target.value)}
                  placeholder="例如：qwen-image-2.0-pro"
                  className={inputClass}
                />
                <p className="text-xs text-gray-500 mt-1">推荐：qwen-image-2.0-pro / qwen-image-2.0</p>
              </div>
              <div>
                <label className={labelClass}>默认尺寸</label>
                <ThemedSelect
                  value={form.default_size ?? '2048*2048'}
                  onChange={v => set('default_size', v)}
                  options={sizes.map(s => ({ value: s, label: s }))}
                  className={selectClass}
                />
              </div>
            </>
          )}

          <div className="mt-4 p-4 bg-gray-50 dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800">
            <p className="text-sm font-medium text-gray-700 mb-2">测试生成</p>
            <div className="flex gap-2">
              <input type="text" value={testPrompt} onChange={e => setTestPrompt(e.target.value)}
                placeholder="输入测试提示词..." className="flex-1 px-4 py-2 bg-gray-100 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-xl text-gray-800 placeholder-gray-500 outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-sm" />
              <button onClick={handleTest} disabled={testLoading || !testPrompt.trim() || !savedToolId || !form.model}
                className="px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-xl hover:shadow-lg transition-all disabled:opacity-50 flex items-center gap-1.5 text-sm">
                {testLoading ? <Loader2 size={14} className="animate-spin" /> : <Image size={14} />}
                生成
              </button>
            </div>
            {testError && <p className="text-red-500 text-xs mt-2">{testError}</p>}
            {testImage && (
              <div className="mt-3">
                <img src={testImage} alt="生成结果" className="max-w-full rounded-xl border border-gray-200 dark:border-zinc-800" />
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex justify-between pt-2">
        <button onClick={step === 1 ? onCancel : () => setStep(1)}
          className="flex items-center gap-1.5 px-5 py-2.5 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 text-gray-700 rounded-xl transition-all text-sm">
          {step > 1 && <ChevronLeft size={15} />}
          {step === 1 ? '取消' : '上一步'}
        </button>
        {step === 1 ? (
          <button onClick={handleNext} disabled={saving || !form.api_key}
            className="flex items-center gap-1.5 px-5 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-xl hover:shadow-lg transition-all disabled:opacity-50 text-sm">
            {saving ? <Loader2 size={14} className="animate-spin" /> : null}
            下一步 <ChevronRight size={15} />
          </button>
        ) : (
          // ✅ 未选择模型时禁用保存
          <button onClick={handleSave} disabled={saving || !canProceedStep2}
            className="flex items-center gap-1.5 px-5 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-xl hover:shadow-lg transition-all disabled:opacity-50 text-sm">
            {saving ? <Loader2 size={14} className="animate-spin" /> : null}
            保存
          </button>
        )}
      </div>
    </div>
  );
};

export default ImageToolWizard;
