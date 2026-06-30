import type { SkillFileOut } from './SkillFileOut'
export type SkillOut = {
  name: string
  content: string
  description?: string | null
  category?: string | null
  scope?: string | null
  session_id?: string | null
  files?: Array<SkillFileOut>
  id: number
  user_id: number
  created_at: string
  updated_at: string
}
