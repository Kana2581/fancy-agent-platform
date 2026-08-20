import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, DefaultService } from '../api'
import { tokenManager } from '../utils/TokenManager'
import { setupApiClient } from '../utils/ApiClient'
import { useAppContext } from '../context/AppContext'

const ERROR_MESSAGES: Record<string, string> = {
  'Invalid email or password': '用户名或密码错误',
  'Email already exists': '邮箱已被注册',
  'Username already exists': '用户名已被占用',
  'User not found': '用户不存在',
}

const extractErrorMessage = (error: unknown): string => {
  if (error instanceof ApiError) {
    if (error.status === 429) {
      return '操作过于频繁，请稍候再试'
    }
    const detail = error.body?.detail
    if (typeof detail === 'string') return ERROR_MESSAGES[detail] ?? detail
  }
  if (error instanceof Error) return error.message
  return '请求失败，请稍后重试'
}
const AuthPage = () => {
  const navigate = useNavigate()
  const { refreshAll } = useAppContext()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  const submitLogin = async () => {
    const loginResult = await DefaultService.loginApiV1AuthLoginPost({ username, password })
    const accessToken = loginResult.access_token
    if (!accessToken) {
      throw new Error('登录响应未返回 access_token')
    }
    tokenManager.setToken(accessToken)
    setupApiClient()
    await refreshAll()
    void navigate('/chat', { replace: true })
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setSuccess('')

    try {
      setLoading(true)
      await submitLogin()
    } catch (submitError) {
      setError(extractErrorMessage(submitError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
        <p className="mb-1 text-xs font-medium text-gray-400 tracking-widest uppercase">
          Fancy Agent
        </p>
        <h1 className="mb-6 text-2xl font-semibold text-gray-900">
          欢迎回来
        </h1>

        <form className="space-y-3" onSubmit={handleSubmit}>
          <input
            className="w-full rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 outline-none transition focus:border-gray-500 focus:ring-1 focus:ring-gray-200"
            placeholder="用户名"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />

          <input
            className="w-full rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 outline-none transition focus:border-gray-500 focus:ring-1 focus:ring-gray-200"
            placeholder="密码"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {error && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
              {error}
            </p>
          )}
          {success && (
            <p className="rounded-xl border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
              {success}
            </p>
          )}

          <button
            className="w-full mt-2 rounded-xl bg-gray-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            disabled={loading}
          >
            {loading ? '提交中...' : '登录'}
          </button>
        </form>

        <p className="mt-5 text-sm text-gray-500">当前不开放自助注册。</p>
      </div>
    </div>
  )
}

export default AuthPage
