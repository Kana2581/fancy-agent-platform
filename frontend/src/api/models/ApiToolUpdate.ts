/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TemplateVariable } from './TemplateVariable'
export type ApiToolUpdate = {
  name?: string | null
  description?: string | null
  url?: string | null
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | null
  headers?: Record<string, string> | null
  param_location?: 'query' | 'body' | 'path_and_query' | 'path_and_body' | null
  request_template?: any
  tool_params?: Array<TemplateVariable> | null
  response_template?: string | null
  response_max_chars?: number | null
}
