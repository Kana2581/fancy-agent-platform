import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Bot, AlertTriangle } from 'lucide-react'
import type { SharedSessionView } from '../api'
import { SessionSharesService } from '../api'
import { MessageBubble } from '../components/message'

type SharedContentItem = {
  type?: string
  text?: string
  image_url?: { url?: string } | string
}

const contentToString = (content: unknown): string => {
  if (content == null) return ''
  if (typeof content === 'string') return content
  if (Array.isArray(content)) {
    return content
      .map((raw): string => {
        if (typeof raw === 'string') return raw
        const item = raw as SharedContentItem
        if (item?.type === 'text' && typeof item?.text === 'string') return item.text
        if (item?.type === 'image_url') {
          const url = typeof item.image_url === 'string' ? item.image_url : item.image_url?.url
          return url ? `![image](${url})` : ''
        }
        return ''
      })
      .filter(Boolean)
      .join('\n\n')
  }
  try {
    return JSON.stringify(content)
  } catch {
    return '[non-serializable]'
  }
}

const SharedSessionPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>()
  const [view, setView] = useState<SharedSessionView | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!slug) return
    let cancelled = false
    void (async () => {
      try {
        const data = await SessionSharesService.viewShared(slug)
        if (!cancelled) setView(data)
      } catch (e) {
        console.error(e)
        if (!cancelled) {
          const err = e as { status?: number; response?: { status?: number } }
          const status = err?.status ?? err?.response?.status
          setError(status === 410 ? '该分享链接已失效或已过期。' : '加载分享内容失败。')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [slug])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <header className="bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800 shadow-lg px-6 py-5 mb-6 flex items-center gap-4">
          <div className="text-4xl">{view?.agent_avatar || '🤖'}</div>
          <div className="flex-1 min-w-0">
            <h1 className="font-semibold text-xl text-gray-800 truncate">
              {view?.session_title || '共享对话'}
            </h1>
            <p className="text-sm text-gray-600 truncate">
              {view?.agent_description || (loading ? '加载中…' : '只读分享视图')}
            </p>
          </div>
          <div className="text-xs text-gray-500 hidden sm:block">
            {view?.expires_at ? `过期：${view.expires_at}` : view ? '永不过期' : ''}
          </div>
        </header>

        {error ? (
          <div className="bg-amber-400/15 border border-amber-400/40 text-amber-800 rounded-xl px-6 py-8 flex items-center gap-3">
            <AlertTriangle size={20} />
            <div className="flex-1">
              <div className="font-medium">{error}</div>
              <div className="text-sm mt-1 text-amber-700/80">
                如果你需要查看完整对话，请联系分享者重新生成链接。
              </div>
            </div>
          </div>
        ) : loading ? (
          <div className="text-center text-gray-500 py-16">加载中…</div>
        ) : view && view.messages.length === 0 ? (
          <div className="text-center text-gray-500 py-16 bg-white dark:bg-zinc-900 rounded-xl border border-gray-200 dark:border-zinc-800">
            <Bot size={32} className="mx-auto mb-2 text-gray-400" />
            该会话暂无消息。
          </div>
        ) : (
          <div className="space-y-6">
            {view?.messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                type={msg.type}
                content={contentToString(msg.content)}
              />
            ))}
          </div>
        )}

        <footer className="mt-10 pt-6 border-t border-gray-200 dark:border-zinc-700 text-center text-xs text-gray-500">
          由 Fancy Agent 分享 ·{' '}
          <Link to="/" className="underline hover:text-gray-700">
            访问平台
          </Link>
        </footer>
      </div>
    </div>
  )
}

export default SharedSessionPage
