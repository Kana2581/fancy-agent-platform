export type TextAnnotation = {
  id: string
  type: 'citation'
  title: string
  cited_text: string
}

export type ContentBlock = {
  id: string
  type: 'text'
  text: string
  annotations?: TextAnnotation[]
}

export type ToolCallData = {
  id?: string
  name?: string
  args?: Record<string, unknown>
  [key: string]: unknown
}

export type UsageMetadata = {
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  [key: string]: unknown
}
