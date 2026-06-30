export type KGNodeOut = {
  id: number
  user_id: number
  graph_id: number
  name: string
  type: string
  description?: string | null
  properties?: Record<string, unknown> | null
  created_at?: string | null
  updated_at?: string | null
}
