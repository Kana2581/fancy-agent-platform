import React, { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'
import { StatsService } from '../api/services/StatsService'
import type { TokenSummary } from '../api/models/TokenSummary'
import type { AgentTokenStat } from '../api/models/AgentTokenStat'
import type { DailyTokenStat } from '../api/models/DailyTokenStat'

const useTickColor = () => {
  const [isDark, setIsDark] = useState(() => localStorage.getItem('chat-theme') === 'dark')
  useEffect(() => {
    const handler = (e: Event) => setIsDark((e as CustomEvent).detail.isDark)
    window.addEventListener('themechange', handler)
    return () => window.removeEventListener('themechange', handler)
  }, [])
  return isDark ? '#f8fafc' : '#111827'
}

const StatsPage: React.FC = () => {
  const tickColor = useTickColor()
  const [summary, setSummary] = useState<TokenSummary | null>(null)
  const [byAgent, setByAgent] = useState<AgentTokenStat[]>([])
  const [daily, setDaily] = useState<DailyTokenStat[]>([])
  const [days, setDays] = useState(30)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading flag for the data fetch below
    setLoading(true)
    Promise.all([
      StatsService.getTokenSummary(),
      StatsService.getTokensByAgent(),
      StatsService.getDailyTokens(days),
    ])
      .then(([s, a, d]) => {
        setSummary(s)
        setByAgent(a.items)
        setDaily(d.items)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days])

  const formatNum = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n))

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold text-gray-800">Token 用量统计</h1>

      {loading ? (
        <div className="text-gray-500 text-sm">加载中...</div>
      ) : (
        <>
          {/* 汇总卡片 */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[
              {
                label: '总输出 Tokens',
                value: formatNum(summary?.total_output_tokens ?? 0),
                color: '',
              },
              {
                label: '总输入 Tokens',
                value: formatNum(summary?.total_input_tokens ?? 0),
                color: 'from-gray-600 to-gray-900',
              },
              {
                label: 'AI 消息数',
                value: String(summary?.total_messages ?? 0),
                color: 'from-gray-500 to-gray-800',
              },
              {
                label: '会话数',
                value: String(summary?.total_sessions ?? 0),
                color: 'from-indigo-400 to-purple-500',
              },
            ].map((card) => (
              <div
                key={card.label}
                className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-5"
              >
                <div className="text-xs text-gray-500 mb-1">{card.label}</div>
                <div
                  className={`text-3xl font-bold bg-${card.color} bg-clip-text text-transparent`}
                >
                  {card.value}
                </div>
              </div>
            ))}
          </div>

          {/* 每日趋势 */}
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-800">每日趋势</h2>
              <div className="flex gap-2">
                {[7, 14, 30].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDays(d)}
                    className={`px-3 py-1 text-xs rounded-xl transition-all ${
                      days === d
                        ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
                        : 'bg-gray-100 dark:bg-zinc-800 text-gray-700 hover:bg-gray-200 dark:hover:bg-zinc-600'
                    }`}
                  >
                    {d} 天
                  </button>
                ))}
              </div>
            </div>
            {daily.length === 0 ? (
              <div className="text-sm text-gray-500 py-8 text-center">暂无数据</div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={daily} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.15)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: tickColor }}
                    tickFormatter={(v: string) => v.slice(5)}
                  />
                  <YAxis tick={{ fontSize: 11, fill: tickColor }} tickFormatter={formatNum} />
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(255,255,255,0.85)',
                      borderRadius: 12,
                      border: 'none',
                      fontSize: 12,
                    }}
                    formatter={(value: unknown) => [formatNum(Number(value ?? 0)), '']}
                  />
                  <Legend wrapperStyle={{ fontSize: 12, color: tickColor }} />
                  <Line
                    type="monotone"
                    dataKey="output_tokens"
                    name="输出 Tokens"
                    stroke="#06b6d4"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="input_tokens"
                    name="输入 Tokens"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* 按 Agent 分布 */}
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 p-5">
            <h2 className="font-semibold text-gray-800 mb-4">按 Agent 分布</h2>
            {byAgent.length === 0 ? (
              <div className="text-sm text-gray-500 py-8 text-center">暂无数据</div>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={Math.max(200, byAgent.length * 48)}>
                  <BarChart
                    data={byAgent}
                    layout="vertical"
                    margin={{ top: 0, right: 16, left: 8, bottom: 0 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(255,255,255,0.15)"
                      horizontal={false}
                    />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11, fill: tickColor }}
                      tickFormatter={formatNum}
                    />
                    <YAxis
                      type="category"
                      dataKey="agent_name"
                      tick={{ fontSize: 11, fill: tickColor }}
                      width={90}
                    />
                    <Tooltip
                      contentStyle={{
                        background: 'rgba(255,255,255,0.85)',
                        borderRadius: 12,
                        border: 'none',
                        fontSize: 12,
                      }}
                      formatter={(value: unknown) => [formatNum(Number(value ?? 0)), '']}
                    />
                    <Legend wrapperStyle={{ fontSize: 12, color: tickColor }} />
                    <Bar
                      dataKey="output_tokens"
                      name="输出 Tokens"
                      fill="#06b6d4"
                      radius={[0, 4, 4, 0]}
                    />
                    <Bar
                      dataKey="input_tokens"
                      name="输入 Tokens"
                      fill="#6366f1"
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>

                {/* 表格 */}
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-gray-500 text-xs border-b border-gray-200 dark:border-zinc-800">
                        <th className="pb-2">Agent</th>
                        <th className="pb-2 text-right">输入</th>
                        <th className="pb-2 text-right">输出</th>
                        <th className="pb-2 text-right">消息数</th>
                      </tr>
                    </thead>
                    <tbody>
                      {byAgent.map((a) => (
                        <tr
                          key={a.agent_id}
                          className="border-b border-gray-100 dark:border-zinc-800/50 hover:bg-gray-50 dark:bg-zinc-900 transition-colors"
                        >
                          <td className="py-2 text-gray-800">{a.agent_name}</td>
                          <td className="py-2 text-right text-gray-700">
                            {formatNum(a.input_tokens)}
                          </td>
                          <td className="py-2 text-right text-gray-700">
                            {formatNum(a.output_tokens)}
                          </td>
                          <td className="py-2 text-right text-gray-600">{a.message_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default StatsPage
