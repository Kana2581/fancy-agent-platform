/**
 * 统一的文件引用类型，收敛 4 种后端响应形状：
 *   - ChatFileResponse  (POST /api/v1/files 上传结果)
 *   - SimpleFile        (ChatResponse.files 内嵌，消息附件)
 *   - WorkspaceFileOut  (GET /api/v1/workspace/{session_id}/files)
 *   - GeneratedImageOut (生图历史)
 *
 * 新 UI 组件应当消费 FileRef，并通过本文件提供的 fromXxx 转换器接入现有 API。
 * 不强制改造已有消费者：旧代码继续直接读各自原始形状，等下次重构时再迁移。
 *
 * Download 鉴权：
 *   - kind='workspace'  → 必须走 fetch + JWT（见 WorkspacesService.downloadFile）
 *   - kind='upload'     → Nginx 公开静态，可直接 <a href download>
 *   - kind='generated'  → 同上，Nginx 公开
 *
 * `downloadProtected` 字段把这层规则物化出来，组件不需要重新推断。
 */

import type { ChatFileResponse } from '../api/models/ChatFileResponse'
import type { SimpleFile } from '../api/models/SimpleFile'
import type { WorkspaceFileOut } from '../api/models/WorkspaceFileOut'
import type { GeneratedImageOut } from '../api/models/GeneratedImageOut'

export type FileRefKind = 'upload' | 'workspace' | 'generated'

export interface FileRef {
  /** 后端主键（ChatFile.id 或 GeneratedImage.id）。同一 kind 内唯一。 */
  id: number
  /** 显示用文件名。SimpleFile 没有文件名时退化为 `file-${id}`。 */
  name: string
  /** 直链 URL。workspace 文件没有公开 URL，此处为空字符串，调用方应改用 downloadFile()。 */
  url: string
  /** 文件大小（字节）。SimpleFile 不携带，可能为 undefined。 */
  size?: number
  /** MIME 类型。SimpleFile/Workspace 不一定带，可能为 undefined。 */
  mime?: string
  /** 文件扩展名（不含点）。生图统一为 'png'。 */
  ext?: string
  /** 决定下载策略与渲染权限。 */
  kind: FileRefKind
  /** true → 必须 fetch+JWT 下载，false → 公开 URL 可直接渲染/下载。 */
  downloadProtected: boolean
}

function inferExtFromName(name: string | null | undefined): string | undefined {
  if (!name) return undefined
  const dot = name.lastIndexOf('.')
  if (dot < 0 || dot === name.length - 1) return undefined
  return name.slice(dot + 1).toLowerCase()
}

export function fromChatFileResponse(f: ChatFileResponse): FileRef {
  return {
    id: f.id,
    name: f.file_name,
    url: f.url,
    size: f.file_size,
    mime: f.content_type ?? undefined,
    ext: f.file_ext,
    kind: f.storage_type === 'workspace' ? 'workspace' : 'upload',
    downloadProtected: f.storage_type === 'workspace',
  }
}

export function fromSimpleFile(f: SimpleFile): FileRef {
  return {
    id: f.id,
    name: `file-${f.id}`,
    url: f.url ?? '',
    mime: f.content_type ?? undefined,
    ext: inferExtFromName(f.url),
    kind: 'upload',
    downloadProtected: false,
  }
}

export function fromWorkspaceFileOut(f: WorkspaceFileOut): FileRef {
  return {
    id: f.file_id,
    name: f.name,
    url: '', // workspace 文件没有公开 URL；调用方须通过 WorkspacesService.downloadFile(id)
    size: f.size,
    ext: f.ext,
    kind: 'workspace',
    downloadProtected: true,
  }
}

export function fromGeneratedImageOut(f: GeneratedImageOut): FileRef {
  return {
    id: f.id,
    name: `generated-${f.id}.png`,
    url: f.image_url,
    mime: 'image/png',
    ext: 'png',
    kind: 'generated',
    downloadProtected: false,
  }
}

/**
 * 触发浏览器下载。公开 URL 走 <a download>；workspace 必须 fetch+JWT 拿 blob 再触发。
 * 调用方传入 workspace 下载器（避免本文件直接依赖 WorkspacesService 形成循环）。
 */
export async function downloadFileRef(
  ref: FileRef,
  workspaceDownloader: (
    id: number,
    fallbackName: string
  ) => Promise<{ blob: Blob; filename: string }>
): Promise<void> {
  if (ref.downloadProtected) {
    const { blob, filename } = await workspaceDownloader(ref.id, ref.name)
    const blobUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(blobUrl)
    return
  }

  if (!ref.url) {
    throw new Error(`FileRef #${ref.id} has no URL and is not download-protected`)
  }
  const a = document.createElement('a')
  a.href = ref.url
  a.download = ref.name
  document.body.appendChild(a)
  a.click()
  a.remove()
}
