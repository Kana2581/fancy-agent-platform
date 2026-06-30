export type UserMemoryOut = {
  id: number
  user_id: number
  key: string
  content: string
  memory_type: 'core' | 'normal'
  category?: string | null
  created_at: string
  updated_at: string
}
