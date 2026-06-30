import type { HelpDocumentSummaryOut } from './HelpDocumentSummaryOut'

export type HelpDocumentOut = HelpDocumentSummaryOut & {
  content: string
  created_at: string
  updated_at: string
}
