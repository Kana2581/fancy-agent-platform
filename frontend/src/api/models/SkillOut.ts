export type SkillFileOut = {
  path: string
  size: number
  type: string
}

export type SkillOut = {
  scope: 'system' | 'user'
  package_path: string
  name: string
  description: string
  package_status: 'ready' | 'invalid'
  error?: string | null
  content_hash?: string | null
  mount_path: string
  files: Array<SkillFileOut>
}
