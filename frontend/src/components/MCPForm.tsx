import React, { useState } from 'react';
import { Save, ChevronDown, ChevronUp, CheckCircle, XCircle } from 'lucide-react';
import ThemedSelect from './ThemedSelect';

interface MCPFormData {
  mcp_name: string;
  transport: string;
  config_json: Record<string, unknown>;
  is_enabled: boolean;
}

interface MCPFormProps {
  form: MCPFormData;
  onChange: (form: MCPFormData) => void;
  onSave: () => void;
  onCancel: () => void;
}

const MCPForm: React.FC<MCPFormProps> = ({ form, onChange, onSave, onCancel }) => {
  const isNew = form.mcp_name === '';
  const [importOpen, setImportOpen] = useState(isNew);
  const [importText, setImportText] = useState('');
  const [importStatus, setImportStatus] = useState<'idle' | 'ok' | 'error'>('idle');
  const [importError, setImportError] = useState('');

  const handleImport = () => {
    try {
      const raw = JSON.parse(importText);
      // 兼容完整格式 { mcpServers: { ... } } 和直接粘贴 server 对象
      const servers = (raw.mcpServers && typeof raw.mcpServers === 'object') ? raw.mcpServers : raw;
      const firstName = Object.keys(servers)[0];
      if (!firstName) throw new Error('未找到有效的 MCP 服务配置');
      const serverCfg = servers[firstName];
      if (typeof serverCfg !== 'object' || serverCfg === null) throw new Error('服务配置格式无效');

      // 优先通过 url+transport/type 判断；有 command 或都不满足时默认 stdio
      const cfgTransport = serverCfg.transport ?? serverCfg.type;
      let transport: string;
      if (serverCfg.url && cfgTransport === 'sse') transport = 'sse';
      else if (serverCfg.url && cfgTransport === 'http') transport = 'http';
      else if (serverCfg.url) transport = 'http';
      else transport = 'stdio';

      onChange({ ...form, mcp_name: firstName, transport, config_json: serverCfg });
      setImportStatus('ok');
      setImportOpen(false);
    } catch (e) {
      setImportStatus('error');
      setImportError(e instanceof Error ? e.message : '无效 JSON');
    }
  };

  const handleImportTextChange = (v: string) => {
    setImportText(v);
    if (importStatus !== 'idle') setImportStatus('idle');
  };

  return (
    <div className="space-y-5">
      {/* 快速导入区域 */}
      <div className="border border-gray-200 dark:border-zinc-700 rounded-2xl overflow-hidden">
        <button
          type="button"
          onClick={() => setImportOpen(o => !o)}
          className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all text-left"
        >
          <span className="text-sm font-medium text-gray-700 dark:text-zinc-300">
            快速导入 MCP 配置 JSON
          </span>
          <span className="flex items-center gap-2">
            {importStatus === 'ok' && (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <CheckCircle size={14} /> 解析成功
              </span>
            )}
            {importOpen ? <ChevronUp size={16} className="text-gray-500" /> : <ChevronDown size={16} className="text-gray-500" />}
          </span>
        </button>

        {importOpen && (
          <div className="px-4 pb-4 pt-3 space-y-3 bg-white dark:bg-zinc-900">
            <p className="text-xs text-gray-500 dark:text-zinc-400">
              粘贴标准 MCP JSON（支持 Claude Desktop 格式，含 <code>mcpServers</code> 键或直接粘贴 server 对象），自动识别名称、传输方式和配置。
            </p>
            <textarea
              value={importText}
              onChange={(e) => handleImportTextChange(e.target.value)}
              placeholder={'{\n  "mcpServers": {\n    "my-tool": {\n      "command": "npx",\n      "args": ["-y", "@some/mcp-server"]\n    }\n  }\n}'}
              rows={7}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none resize-none font-mono text-sm transition-all text-gray-800 dark:text-zinc-200 placeholder-gray-400"
            />
            {importStatus === 'error' && (
              <div className="flex items-start gap-2 text-xs text-red-600">
                <XCircle size={14} className="mt-0.5 shrink-0" />
                <span>{importError}</span>
              </div>
            )}
            <button
              type="button"
              onClick={handleImport}
              disabled={!importText.trim()}
              className="px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm rounded-xl hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-all font-medium"
            >
              解析并填入
            </button>
          </div>
        )}
      </div>

      {/* 原有字段 */}
      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">工具名称 *</label>
        <input
          type="text"
          value={form.mcp_name}
          onChange={(e) => onChange({ ...form, mcp_name: e.target.value })}
          placeholder="例如：Web Search"
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none transition-all text-gray-800 placeholder-gray-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">传输方式 *</label>
        <ThemedSelect
          value={form.transport}
          onChange={(v) => onChange({ ...form, transport: v })}
          options={[
            { value: 'stdio', label: 'stdio' },
            { value: 'http', label: 'http' },
            { value: 'sse', label: 'sse' },
          ]}
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none transition-all text-gray-800 dark:text-white"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-800 mb-2">配置 JSON</label>
        <textarea
          value={JSON.stringify(form.config_json, null, 2)}
          onChange={(e) => {
            try {
              onChange({ ...form, config_json: JSON.parse(e.target.value) });
            } catch {
              /* ignore invalid JSON while the user is still typing */
            }
          }}
          placeholder='{"key": "value"}'
          rows={5}
          className="w-full px-4 py-3 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:ring-1 focus:ring-gray-300 dark:focus:ring-zinc-600 focus:border-gray-500 dark:focus:border-zinc-400 outline-none resize-none font-mono text-sm transition-all text-gray-800 placeholder-gray-500"
        />
      </div>

      <div className="flex items-center gap-3">
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={form.is_enabled}
            onChange={(e) => onChange({ ...form, is_enabled: e.target.checked })}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gray-900 dark:peer-checked:bg-white"></div>
        </label>
        <span className="text-sm text-gray-700">创建后立即启用</span>
      </div>

      <div className="flex gap-3 pt-4">
        <button
          onClick={onSave}
          className="flex-1 px-4 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:opacity-90 transition-all flex items-center justify-center gap-2 font-medium"
        >
          <Save size={18} />
          保存
        </button>
        <button
          onClick={onCancel}
          className="px-6 py-3 bg-gray-200 dark:bg-zinc-700 text-gray-700 rounded-2xl hover:bg-white/40 transition-all"
        >
          取消
        </button>
      </div>
    </div>
  );
};

export default MCPForm;
