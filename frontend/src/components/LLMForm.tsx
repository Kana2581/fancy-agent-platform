import React, { useState } from 'react';
import { Save, Plug, Loader2, CheckCircle2, XCircle, MessageCirclePlus } from 'lucide-react';
import ThemedSelect from './ThemedSelect';
import { LlmModelsService } from '../api';

interface LLMFormData {
  provider: string;
  model_name: string;
  base_url: string;
  api_key: string;
}

interface LLMFormProps {
  form: LLMFormData;
  onChange: (form: LLMFormData) => void;
  onSave: () => void | Promise<void>;
  onSaveAndStart?: () => void | Promise<void>;
  onCancel: () => void;
  editingId?: number | null;
  savingAction?: 'save' | 'start' | null;
}

const LLMForm: React.FC<LLMFormProps> = ({
  form,
  onChange,
  onSave,
  onSaveAndStart,
  onCancel,
  editingId,
  savingAction = null,
}) => {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const isSaving = savingAction !== null;

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await LlmModelsService.testLlmApiV1LlmTestPost({
        provider: form.provider,
        model_name: form.model_name,
        base_url: form.base_url || null,
        api_key: form.api_key || null,
        llm_id: editingId ?? null,
      });
      setTestResult(res);
    } catch (e: any) {
      const detail = e?.body?.detail || e?.message || '请求失败';
      setTestResult({ success: false, message: typeof detail === 'string' ? detail : JSON.stringify(detail) });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">提供商 *</label>
        <ThemedSelect
          value={form.provider}
          onChange={(v) => onChange({ ...form, provider: v })}
          options={[
            { value: 'OpenAI', label: 'OpenAI' },
            { value: 'Anthropic', label: 'Anthropic' },
            { value: 'Google', label: 'Google' },
            { value: 'Azure', label: 'Azure' },
            { value: 'Custom', label: 'Custom' },
          ]}
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none transition-all text-gray-800 dark:text-white"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">模型名称 *</label>
        <input
          type="text"
          value={form.model_name}
          onChange={(e) => onChange({ ...form, model_name: e.target.value })}
          placeholder="例如：gpt-4, claude-3-sonnet"
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none transition-all text-gray-800 placeholder-gray-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">Base URL</label>
        <input
          type="text"
          value={form.base_url}
          onChange={(e) => onChange({ ...form, base_url: e.target.value })}
          placeholder="https://api.openai.com"
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none transition-all text-gray-800 placeholder-gray-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">API Key *</label>
        <input
          type="password"
          value={form.api_key}
          onChange={(e) => onChange({ ...form, api_key: e.target.value })}
          placeholder="sk-..."
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none transition-all text-gray-800 placeholder-gray-500"
        />
        <p className="text-xs text-gray-600 mt-2">API Key 将被加密存储{editingId ? '，测试时留空会使用已保存的 Key' : ''}</p>
      </div>

      {testResult && (
        <div
          className={`flex items-start gap-2 p-3 rounded-2xl border text-sm ${
            testResult.success
              ? 'bg-green-500/15 border-green-400/40 text-green-800'
              : 'bg-red-500/15 border-red-400/40 text-red-800'
          }`}
        >
          {testResult.success ? (
            <CheckCircle2 size={18} className="flex-shrink-0 mt-0.5" />
          ) : (
            <XCircle size={18} className="flex-shrink-0 mt-0.5" />
          )}
          <span className="break-all">{testResult.message}</span>
        </div>
      )}

      <div className="flex gap-3 pt-4">
        <button
          onClick={handleTest}
          disabled={testing || isSaving || !form.provider || !form.model_name}
          className="px-4 py-3 bg-gray-200 dark:bg-zinc-700 text-gray-800 rounded-2xl hover:bg-white/40 transition-all flex items-center justify-center gap-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {testing ? <Loader2 size={18} className="animate-spin" /> : <Plug size={18} />}
          {testing ? '测试中...' : '测试连接'}
        </button>
        <button
          onClick={onSave}
          disabled={isSaving || !form.provider || !form.model_name}
          className="flex-1 px-4 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:opacity-90 transition-all flex items-center justify-center gap-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
        >
          {savingAction === 'save' ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
          {savingAction === 'save' ? '保存中...' : '保存'}
        </button>
        {onSaveAndStart && (
          <button
            onClick={onSaveAndStart}
            disabled={isSaving || !form.provider || !form.model_name}
            className="flex-1 px-4 py-3 bg-gray-900/80 text-white rounded-2xl hover:bg-gray-900 hover:shadow-lg transition-all flex items-center justify-center gap-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {savingAction === 'start' ? <Loader2 size={18} className="animate-spin" /> : <MessageCirclePlus size={18} />}
            {savingAction === 'start' ? '创建中...' : '保存并开始聊天'}
          </button>
        )}
        <button
          onClick={onCancel}
          disabled={isSaving}
          className="px-6 py-3 bg-gray-200 dark:bg-zinc-700 text-gray-700 rounded-2xl hover:bg-white/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          取消
        </button>
      </div>
    </div>
  );
};

export default LLMForm;
