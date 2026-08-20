export type ResponseContentBlock = string | Record<string, unknown>
export type ResponseMessageContent = string | ResponseContentBlock[] | Record<string, unknown>

export interface ParsedResponseContent {
  content: string
  reasoningSummary: string
}

function textFrom(value: unknown): string {
  if (typeof value === 'string') return value
  if (Array.isArray(value)) return value.map(textFrom).filter(Boolean).join('')
  if (!value || typeof value !== 'object') return ''

  const block = value as Record<string, unknown>
  for (const key of ['text', 'content', 'value']) {
    if (typeof block[key] === 'string') return block[key]
  }
  return ''
}

function imageUrl(block: Record<string, unknown>): string | null {
  const candidate = block.image_url ?? block.url
  if (typeof candidate === 'string') return candidate
  if (candidate && typeof candidate === 'object') {
    const url = (candidate as Record<string, unknown>).url
    return typeof url === 'string' ? url : null
  }
  return null
}

/** Split native Responses content into user-visible output and reasoning summaries. */
export function parseResponseContent(content: unknown): ParsedResponseContent {
  if (content === null || content === undefined) return { content: '', reasoningSummary: '' }
  if (typeof content === 'string') return { content, reasoningSummary: '' }
  if (!Array.isArray(content)) {
    try {
      return { content: JSON.stringify(content, null, 2), reasoningSummary: '' }
    } catch {
      return { content: '[non-serializable]', reasoningSummary: '' }
    }
  }

  const visible: string[] = []
  const reasoning: string[] = []
  for (const item of content) {
    if (typeof item === 'string') {
      visible.push(item)
      continue
    }
    if (!item || typeof item !== 'object') continue
    const block = item as Record<string, unknown>
    const type = typeof block.type === 'string' ? block.type : ''

    if (type === 'reasoning') {
      const summary = block.summary
      const extracted = textFrom(summary ?? block.text ?? block.content)
      if (extracted) reasoning.push(extracted)
    } else if (['text', 'output_text', 'input_text'].includes(type)) {
      const text = textFrom(block.text ?? block.content)
      if (text) visible.push(text)
      const annotations = Array.isArray(block.annotations) ? block.annotations : []
      for (const annotation of annotations) {
        if (!annotation || typeof annotation !== 'object') continue
        const itemAnnotation = annotation as Record<string, unknown>
        const citation = itemAnnotation.url_citation
        const citationRecord = citation && typeof citation === 'object'
          ? citation as Record<string, unknown>
          : undefined
        const url = itemAnnotation.url ?? citationRecord?.url
        const title = itemAnnotation.title ?? citationRecord?.title ?? url
        if (typeof url === 'string') visible.push(` [${String(title)}](${url})`)
      }
    } else if (['image', 'image_url', 'input_image', 'output_image'].includes(type)) {
      const url = imageUrl(block)
      if (url) visible.push(`![图片](${url})`)
    } else if (['function_call_output', 'tool_result', 'computer_call_output'].includes(type)) {
      const output = textFrom(block.output ?? block.content)
      if (output) visible.push(output)
    }
  }

  return { content: visible.join(''), reasoningSummary: reasoning.join('\n\n') }
}
