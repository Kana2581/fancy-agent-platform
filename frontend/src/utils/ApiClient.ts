import axios from 'axios'
import toast from 'react-hot-toast'
import { OpenAPI } from '../api/'
import { tokenManager } from './TokenManager'

let _handling401 = false

export const handleUnauthorized = () => {
  if (_handling401) return
  _handling401 = true
  tokenManager.removeToken()
  toast.error('登录已过期，请重新登录')
  window.location.replace('/login')
}

axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      handleUnauthorized()
    }
    return Promise.reject(error instanceof Error ? error : new Error(String(error)))
  }
)

export const setupApiClient = () => {
  OpenAPI.BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'
  OpenAPI.WITH_CREDENTIALS = true

  OpenAPI.TOKEN = () => Promise.resolve(tokenManager.getToken() ?? '')
}
