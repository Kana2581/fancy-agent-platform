import React from 'react'
import { ArrowLeft, Eye, EyeOff } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useHideIntermediatePref } from '../hooks/useUIPreferences'

const PreferencesPage: React.FC = () => {
  const navigate = useNavigate()
  const [hideIntermediate, setHideIntermediate] = useHideIntermediatePref()

  return (
    <div className="p-8 overflow-y-auto">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <button
            onClick={() => navigate('/chat')}
            className="flex items-center gap-2 px-3 py-2 bg-gray-200 dark:bg-zinc-700 hover:bg-gray-300 dark:hover:bg-zinc-600 rounded-xl transition"
          >
            <ArrowLeft size={16} />
            返回
          </button>
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-800 dark:text-zinc-100">界面偏好</h2>
            <p className="text-sm text-gray-600 dark:text-zinc-400 mt-1">
              个性化设置，仅影响当前浏览器
            </p>
          </div>
          <div className="w-[88px]" />
        </div>

        {/* Chat display preferences card */}
        <div className="bg-white dark:bg-zinc-900 rounded-xl p-6 border border-gray-200 dark:border-zinc-700 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-zinc-100 mb-1">聊天显示</h3>
          <p className="text-sm text-gray-500 dark:text-zinc-400 mb-5">
            控制聊天页中过程性消息（工具调用、工具结果等）的展示方式。
          </p>

          <div className="bg-gray-50 dark:bg-zinc-800/40 rounded-2xl border border-gray-200 dark:border-zinc-700 px-5 py-4 flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-cyan-400/15 text-cyan-600 dark:text-cyan-300 flex items-center justify-center shrink-0">
              {hideIntermediate ? <EyeOff size={18} /> : <Eye size={18} />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="font-medium text-gray-800 dark:text-zinc-100">
                    隐藏中间过程消息
                  </div>
                  <p className="text-xs text-gray-500 dark:text-zinc-400 mt-0.5">
                    开启后，工具调用与工具返回将默认折叠成一条提示，仅显示最终回答；点击折叠条可临时展开。
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={hideIntermediate}
                  onClick={() => setHideIntermediate(!hideIntermediate)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors ${
                    hideIntermediate ? 'bg-cyan-500' : 'bg-gray-300 dark:bg-zinc-600'
                  }`}
                >
                  <span
                    className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
                      hideIntermediate ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PreferencesPage
