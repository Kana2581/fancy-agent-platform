/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SimpleFile } from './SimpleFile'
import type { StructuredOutputArtifact } from './StructuredOutputSchema'
import type { ResponseMessageContent } from '../../utils/responseContent'
export type ChatResponse = {
  id: string
  content: ResponseMessageContent
  reasoning_summary?: string | null
  type: string
  name?: string | null
  parent_id?: string | null
  tool_calls?: Array<Record<string, any>> | null
  files?: Array<SimpleFile> | null
  usage_metadata?: Record<string, any> | null
  approval_status?: string | null
  artifact?: StructuredOutputArtifact | null
}
