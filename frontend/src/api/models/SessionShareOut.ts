export type SessionShareOut = {
  id: number
  session_id: string
  slug: string
  enabled: boolean
  expires_at?: string | null
  view_count: number
  created_at: string
  updated_at: string
}

export type SessionShareCreate = {
  expires_in_hours?: number | null
}

export type SharedMessage = {
  id: string
  type: string
  content: unknown
  name?: string | null
  created_at: string
}

export type SharedSessionView = {
  slug: string
  session_title?: string | null
  agent_avatar?: string | null
  agent_description?: string | null
  messages: Array<SharedMessage>
  created_at: string
  expires_at?: string | null
}
