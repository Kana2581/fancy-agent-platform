export type KGEdgeOut = {
  id: number
  user_id: number
  graph_id: number
  source_node_id: number
  target_node_id: number
  relation: string
  properties?: Record<string, unknown> | null
  created_at?: string | null
  updated_at?: string | null
}
