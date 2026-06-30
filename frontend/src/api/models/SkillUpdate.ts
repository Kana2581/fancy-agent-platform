import type { SkillFileIn } from './SkillFileIn'
export type SkillUpdate = {
  name?: string | null
  content?: string | null
  description?: string | null
  category?: string | null
  files?: Array<SkillFileIn> | null
}
