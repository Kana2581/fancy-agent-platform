import React, { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Plus, Trash2, X, Webhook, RefreshCcw, Copy, Check, Power } from 'lucide-react'
import { writeToClipboard } from '../utils/clipboard'
import { useNavigate } from 'react-router-dom'
import type { AgentWebhookOut, AgentWebhookOutWithSecret } from '../api'
import { AgentWebhooksService, OpenAPI } from '../api'
import { useAppContext } from '../context/AppContext'
import ThemedSelect from '../components/ThemedSelect'

const getApiOrigin = () => {
  const raw = OpenAPI.BASE || (import.meta.env.VITE_API_BASE as string) || ''
  if (raw && /^https?:\/\//i.test(raw)) return raw.replace(/\/$/, '')
  return window.location.origin
}

interface CreatedSecret {
  webhook: AgentWebhookOutWithSecret
  fresh: boolean // 是否是刚刚创建/重置的
}

const AgentWebhooksPage: React.FC = () => {
  const navigate = useNavigate()
  const { agents } = useAppContext()
  const agentMap = useMemo(() => new Map(agents.map((a) => [a.id, a])), [agents])

  const [hooks, setHooks] = useState<AgentWebhookOut[]>([])
  const [loading, setLoading] = useState(true)

  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [agentId, setAgentId] = useState<number | ''>('')
  const [channel, setChannel] = useState<'generic' | 'telegram' | 'dingtalk' | 'discord'>('generic')
  const [telegramBotToken, setTelegramBotToken] = useState('')
  const [dingtalkAppSecret, setDingtalkAppSecret] = useState('')
  const [discordPublicKey, setDiscordPublicKey] = useState('')
  const [saving, setSaving] = useState(false)

  const [secretInfo, setSecretInfo] = useState<CreatedSecret | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [codeTab, setCodeTab] = useState<'bash' | 'powershell'>('bash')

  const load = async () => {
    setLoading(true)
    try {
      const data = await AgentWebhooksService.listWebhooks()
      setHooks(data)
    } catch (e) {
      console.error('加载 Webhook 失败:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const triggerUrl = (hook: Pick<AgentWebhookOut, 'slug' | 'channel'>) => {
    const path =
      hook.channel === 'telegram'
        ? `/api/v1/telegram/webhooks/${hook.slug}`
        : hook.channel === 'dingtalk'
          ? `/api/v1/dingtalk/webhooks/${hook.slug}`
          : hook.channel === 'discord'
            ? `/api/v1/discord/interactions/${hook.slug}`
            : `/api/v1/webhooks/${hook.slug}`
    return `${getApiOrigin()}${path}`
  }

  const copy = async (key: string, value: string) => {
    try {
      await writeToClipboard(value)
      setCopiedKey(key)
      setTimeout(() => setCopiedKey((prev) => (prev === key ? null : prev)), 1500)
    } catch (e) {
      console.error(e)
    }
  }

  const isCreateFormInvalid =
    !name.trim() ||
    agentId === '' ||
    (channel === 'telegram' && !telegramBotToken.trim()) ||
    (channel === 'dingtalk' && !dingtalkAppSecret.trim()) ||
    (channel === 'discord' && !discordPublicKey.trim())

  const handleCreate = async () => {
    if (isCreateFormInvalid) return
    setSaving(true)
    try {
      const created = await AgentWebhooksService.createWebhook({
        name: name.trim(),
        agent_id: Number(agentId),
        channel,
        telegram_bot_token: channel === 'telegram' ? telegramBotToken.trim() : null,
        dingtalk_app_secret: channel === 'dingtalk' ? dingtalkAppSecret.trim() : null,
        discord_public_key: channel === 'discord' ? discordPublicKey.trim() : null,
      })
      setHooks((prev) => [created, ...prev])
      setSecretInfo({ webhook: created, fresh: true })
      setShowCreate(false)
      setName('')
      setAgentId('')
      setChannel('generic')
      setTelegramBotToken('')
      setDingtalkAppSecret('')
      setDiscordPublicKey('')
    } catch (e) {
      console.error(e)
      alert('创建失败')
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (hook: AgentWebhookOut) => {
    try {
      const updated = await AgentWebhooksService.updateWebhook(hook.id, { enabled: !hook.enabled })
      setHooks((prev) => prev.map((h) => (h.id === updated.id ? updated : h)))
    } catch (e) {
      console.error(e)
      alert('更新失败')
    }
  }

  const handleRegenerate = async (hook: AgentWebhookOut) => {
    if (!confirm(`重置「${hook.name}」的 secret？旧的密钥将立刻失效。`)) return
    try {
      const updated = await AgentWebhooksService.regenerateSecret(hook.id)
      setHooks((prev) => prev.map((h) => (h.id === updated.id ? updated : h)))
      setSecretInfo({ webhook: updated, fresh: true })
    } catch (e) {
      console.error(e)
      alert('重置失败')
    }
  }

  const handleDelete = async (hook: AgentWebhookOut) => {
    if (!confirm(`删除 Webhook「${hook.name}」？此操作不可恢复。`)) return
    try {
      await AgentWebhooksService.deleteWebhook(hook.id)
      setHooks((prev) => prev.filter((h) => h.id !== hook.id))
    } catch (e) {
      console.error(e)
      alert('删除失败')
    }
  }

  const setupSnippet = (hook: AgentWebhookOutWithSecret, shell: 'bash' | 'powershell') => {
    const url = triggerUrl(hook)
    if (hook.channel === 'dingtalk') {
      return `在钉钉机器人开发配置中启用 HTTP 模式：\n1. 将消息接收地址设置为：${url}\n2. 将 AppSecret 填入本页面创建表单的 DingTalk AppSecret\n3. 在群里 @机器人 后，系统会读取回调中的 text.content，执行 Agent，并通过 sessionWebhook 回群。`
    }
    if (hook.channel === 'discord') {
      return `在 Discord Developer Portal 中配置 Slash Command：\n1. 进入 Applications → 你的应用 → General Information，复制 Public Key 填入本页面\n2. 将 Interactions Endpoint URL 设置为：${url}\n3. 用 Discord API 注册命令，示例：\ncurl -X PUT "https://discord.com/api/v10/applications/<application-id>/commands" \\\n  -H "Authorization: Bot <bot-token>" \\\n  -H "Content-Type: application/json" \\\n  -d '[{"name":"ask","description":"Ask the bound Agent","type":1,"options":[{"name":"prompt","description":"Message for the Agent","type":3,"required":true}]}]'\n4. 用户执行 /ask prompt:你的问题 后，本平台会先 deferred response，再把 Agent 回复写回 Discord。`
    }
    if (shell === 'bash') {
      return hook.channel === 'telegram'
        ? `BOT_TOKEN='<your-bot-token>'\nWEBHOOK_URL='${url}'\nSECRET_TOKEN='${hook.secret}'\ncurl -X POST "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \\\n  -H "Content-Type: application/json" \\\n  -d '{"url":"'"$WEBHOOK_URL"'","secret_token":"'"$SECRET_TOKEN"'","allowed_updates":["message"],"drop_pending_updates":true}'`
        : `SECRET='${hook.secret}'\nBODY='{"content":"hello"}'\nSIG=$(printf %s "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')\ncurl -X POST "${url}" \\\n  -H "X-Signature: sha256=$SIG" \\\n  -H "Content-Type: application/json" \\\n  --data-raw "$BODY"`
    }
    return hook.channel === 'telegram'
      ? `$botToken = '<your-bot-token>'\n$webhookUrl = '${url}'\n$secretToken = '${hook.secret}'\n$body = @{ url = $webhookUrl; secret_token = $secretToken; allowed_updates = @('message'); drop_pending_updates = $true } | ConvertTo-Json -Compress\ncurl.exe -X POST "https://api.telegram.org/bot$botToken/setWebhook" \`\n  -H "Content-Type: application/json" \`\n  --data-raw $body`
      : `$secret = '${hook.secret}'\n$body = '{"content":"hello"}'\n$bodyFile = Join-Path $env:TEMP 'webhook-body.json'\n[IO.File]::WriteAllText($bodyFile, $body, [Text.UTF8Encoding]::new($false))\n$bodyBytes = [IO.File]::ReadAllBytes($bodyFile)\n$hmac = [Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($secret))\n$sig = [BitConverter]::ToString($hmac.ComputeHash($bodyBytes)).Replace('-', '').ToLower()\ncurl.exe -X POST "${url}" \`\n  -H "X-Signature: sha256=$sig" \`\n  -H "Content-Type: application/json" \`\n  --data-binary "@$bodyFile"`
  }

  return (
    <div className="p-8 overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 px-3 py-2 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-50 dark:bg-zinc-800/300 rounded-xl transition"
          >
            <ArrowLeft size={16} />
            返回
          </button>
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-800">入站 Webhook</h2>
            <p className="text-sm text-gray-600 mt-1">
              通过 HTTP POST 触发 Agent 执行，请求需带{' '}
              <code className="px-1 bg-black/10 rounded">X-Signature: sha256=&lt;HMAC&gt;</code>
            </p>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="px-5 py-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl   transition-all flex items-center gap-2 font-medium"
          >
            <Plus size={20} />
            新建 Webhook
          </button>
        </div>

        {loading ? (
          <div className="text-center text-gray-500 py-16">加载中...</div>
        ) : hooks.length === 0 ? (
          <div className="text-center py-20">
            <Webhook size={48} className="mx-auto text-gray-400 mb-3" />
            <p className="text-gray-600 mb-2">还没有 Webhook</p>
            <p className="text-sm text-gray-500">绑定一个 Agent，外部系统就能通过 HTTP 调用它</p>
          </div>
        ) : (
          <div className="space-y-4">
            {hooks.map((hook) => {
              const agent = agentMap.get(hook.agent_id)
              const url = triggerUrl(hook)
              return (
                <div
                  key={hook.id}
                  className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-6 shadow-lg"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-lg text-gray-800 truncate">
                          {hook.name}
                        </h3>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                            hook.enabled
                              ? 'bg-emerald-400/20 text-emerald-700 border-emerald-400/40'
                              : 'bg-gray-400/20 text-gray-600 border-gray-400/40'
                          }`}
                        >
                          {hook.enabled ? '已启用' : '已停用'}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded-full border border-gray-300 text-gray-600">
                          {hook.channel === 'telegram'
                            ? 'Telegram'
                            : hook.channel === 'dingtalk'
                              ? 'DingTalk'
                              : hook.channel === 'discord'
                                ? 'Discord'
                                : 'HTTP'}
                        </span>
                      </div>
                      <div className="text-sm text-gray-600">
                        绑定 Agent：
                        {agent
                          ? `${agent.avatar ?? ''} ${agent.description ?? `#${agent.id}`}`
                          : `#${hook.agent_id}`}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        触发次数 {hook.trigger_count}
                        {hook.last_triggered_at && ` · 最近触发 ${hook.last_triggered_at}`}
                      </div>

                      <div className="mt-3 flex items-center gap-2 bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800 px-3 py-2">
                        <code className="flex-1 text-xs text-gray-700 break-all">{url}</code>
                        <button
                          onClick={() => copy(`url-${hook.id}`, url)}
                          className="p-1.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition"
                          title="复制 URL"
                        >
                          {copiedKey === `url-${hook.id}` ? (
                            <Check size={14} className="text-emerald-600" />
                          ) : (
                            <Copy size={14} className="text-gray-700" />
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleToggle(hook)}
                        className="p-2 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-xl transition"
                        title={hook.enabled ? '停用' : '启用'}
                      >
                        <Power
                          size={15}
                          className={hook.enabled ? 'text-emerald-600' : 'text-gray-600'}
                        />
                      </button>
                      <button
                        onClick={() => handleRegenerate(hook)}
                        className="p-2 bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-xl transition"
                        title="重置 secret"
                      >
                        <RefreshCcw size={15} className="text-gray-700" />
                      </button>
                      <button
                        onClick={() => handleDelete(hook)}
                        className="p-2 bg-gray-100 dark:bg-zinc-800 hover:bg-red-100 hover:text-red-600 text-gray-700 rounded-xl transition"
                        title="删除"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 创建弹窗 */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-50 dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 w-full max-w-md">
            <div className="flex items-center justify-between p-6 pb-4 border-b border-gray-200 dark:border-zinc-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg- rounded-2xl flex items-center justify-center">
                  <Webhook size={20} className="text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800">新建 Webhook</h3>
              </div>
              <button
                onClick={() => setShowCreate(false)}
                className="p-2 hover:bg-black/10 rounded-xl transition"
              >
                <X size={20} />
              </button>
            </div>
            <div className="px-6 pb-6 space-y-4 pt-4">
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="如：GitHub 推送告警"
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  类型 <span className="text-red-500">*</span>
                </label>
                <ThemedSelect
                  value={channel}
                  onChange={(value) =>
                    setChannel(
                      value === 'telegram'
                        ? 'telegram'
                        : value === 'dingtalk'
                          ? 'dingtalk'
                          : value === 'discord'
                            ? 'discord'
                            : 'generic'
                    )
                  }
                  options={[
                    { value: 'generic', label: '普通 HTTP Webhook' },
                    { value: 'telegram', label: 'Telegram Bot' },
                    { value: 'dingtalk', label: 'DingTalk Bot' },
                    { value: 'discord', label: 'Discord Slash Command' },
                  ]}
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">
                  绑定 Agent <span className="text-red-500">*</span>
                </label>
                <ThemedSelect
                  value={agentId}
                  onChange={(value) => setAgentId(value === '' ? '' : Number(value))}
                  placeholder="请选择 Agent"
                  options={[
                    { value: '', label: '请选择 Agent' },
                    ...agents.map((a) => ({
                      value: a.id,
                      label: `${a.avatar ?? ''} ${a.description ?? `#${a.id}`}`,
                    })),
                  ]}
                  className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800"
                />
              </div>
              {channel === 'telegram' && (
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Telegram Bot Token <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="password"
                    value={telegramBotToken}
                    onChange={(e) => setTelegramBotToken(e.target.value)}
                    placeholder="123456:ABC-DEF..."
                    className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800"
                  />
                </div>
              )}
              {channel === 'dingtalk' && (
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    DingTalk AppSecret <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="password"
                    value={dingtalkAppSecret}
                    onChange={(e) => setDingtalkAppSecret(e.target.value)}
                    placeholder="钉钉机器人应用的 AppSecret"
                    className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800"
                  />
                </div>
              )}
              {channel === 'discord' && (
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    Discord Public Key <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="password"
                    value={discordPublicKey}
                    onChange={(e) => setDiscordPublicKey(e.target.value)}
                    placeholder="Discord 应用 General Information 里的 Public Key"
                    className="w-full px-4 py-2.5 bg-white dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-2xl focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-zinc-500/50 text-gray-800"
                  />
                </div>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setShowCreate(false)}
                  className="flex-1 py-2.5 bg-gray-200 dark:bg-zinc-700 hover:bg-white/40 text-gray-700 rounded-2xl transition font-medium"
                >
                  取消
                </button>
                <button
                  onClick={handleCreate}
                  disabled={saving || isCreateFormInvalid}
                  className="flex-1 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-2xl hover:shadow-lg transition font-medium disabled:opacity-50"
                >
                  {saving ? '创建中...' : '创建'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* secret 展示弹窗（一次性） */}
      {secretInfo && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-50 dark:bg-zinc-900 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700 w-full max-w-lg flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-6 pb-4 border-b border-gray-200 dark:border-zinc-800 shrink-0">
              <h3 className="text-xl font-bold text-gray-800">
                {secretInfo.fresh ? '请立即复制 secret' : 'Webhook 密钥'}
              </h3>
              <button
                onClick={() => setSecretInfo(null)}
                className="p-2 hover:bg-black/10 rounded-xl transition"
              >
                <X size={20} />
              </button>
            </div>
            <div className="px-6 pb-6 pt-4 space-y-4 overflow-y-auto">
              <div className="bg-amber-400/15 border border-amber-400/40 text-amber-800 text-sm rounded-2xl px-4 py-3">
                {secretInfo.webhook.channel === 'dingtalk'
                  ? 'DingTalk AppSecret 已保存；将 URL 配到钉钉机器人 HTTP 模式即可。'
                  : secretInfo.webhook.channel === 'discord'
                    ? 'Discord Public Key 已保存；将 URL 配到 Discord Interactions Endpoint 即可。'
                    : '此 secret 只显示这一次，关闭后将无法再次查看，请立刻保存。'}
              </div>
              <div>
                <label className="text-xs text-gray-600 mb-1 block">URL</label>
                <div className="flex items-center gap-2 bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800 px-3 py-2">
                  <code className="flex-1 text-xs text-gray-700 break-all">
                    {triggerUrl(secretInfo.webhook)}
                  </code>
                  <button
                    onClick={() => copy('modal-url', triggerUrl(secretInfo.webhook))}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition"
                  >
                    {copiedKey === 'modal-url' ? (
                      <Check size={14} className="text-emerald-600" />
                    ) : (
                      <Copy size={14} className="text-gray-700" />
                    )}
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-600 mb-1 block">
                  {secretInfo.webhook.channel === 'telegram'
                    ? 'Telegram Secret Token'
                    : secretInfo.webhook.channel === 'dingtalk'
                      ? '内部 Secret（钉钉无需配置）'
                      : secretInfo.webhook.channel === 'discord'
                        ? '内部 Secret（Discord 无需配置）'
                        : 'Secret'}
                </label>
                <div className="flex items-center gap-2 bg-white dark:bg-zinc-900 rounded-2xl border border-gray-200 dark:border-zinc-800 px-3 py-2">
                  <code className="flex-1 text-xs text-gray-700 break-all">
                    {secretInfo.webhook.secret}
                  </code>
                  <button
                    onClick={() => copy('modal-secret', secretInfo.webhook.secret)}
                    className="p-1.5 hover:bg-gray-200 dark:hover:bg-zinc-600 rounded-lg transition"
                  >
                    {copiedKey === 'modal-secret' ? (
                      <Check size={14} className="text-emerald-600" />
                    ) : (
                      <Copy size={14} className="text-gray-700" />
                    )}
                  </button>
                </div>
              </div>
              <div className="text-xs text-gray-600 bg-black/5 rounded-2xl overflow-hidden">
                <div className="flex border-b border-black/10">
                  {secretInfo.webhook.channel !== 'dingtalk' &&
                    secretInfo.webhook.channel !== 'discord' && (
                      <>
                        <button
                          onClick={() => setCodeTab('bash')}
                          className={`px-4 py-2 font-medium transition ${
                            codeTab === 'bash'
                              ? 'bg-black/10 text-gray-800'
                              : 'hover:bg-black/5 text-gray-500'
                          }`}
                        >
                          Bash / Git Bash
                        </button>
                        <button
                          onClick={() => setCodeTab('powershell')}
                          className={`px-4 py-2 font-medium transition ${
                            codeTab === 'powershell'
                              ? 'bg-black/10 text-gray-800'
                              : 'hover:bg-black/5 text-gray-500'
                          }`}
                        >
                          PowerShell
                        </button>
                      </>
                    )}
                  <div className="flex-1 flex justify-end items-center pr-2">
                    <button
                      onClick={() => copy('modal-code', setupSnippet(secretInfo.webhook, codeTab))}
                      className="p-1.5 hover:bg-black/10 rounded-lg transition"
                      title="复制"
                    >
                      {copiedKey === 'modal-code' ? (
                        <Check size={13} className="text-emerald-600" />
                      ) : (
                        <Copy size={13} className="text-gray-500" />
                      )}
                    </button>
                  </div>
                </div>
                <div className="px-4 py-3 leading-relaxed">
                  <pre className="whitespace-pre-wrap break-all">
                    {setupSnippet(secretInfo.webhook, codeTab)}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AgentWebhooksPage
