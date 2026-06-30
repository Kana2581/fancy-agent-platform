/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ParamConfig } from './ParamConfig'
import type { ResponseExtract } from './ResponseExtract'
export type ApiToolOut = {
  name: string
  description?: string | null
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  headers?: Record<string, string>
  param_location?: 'query' | 'body' | 'path_and_query' | 'path_and_body'
  fixed_params?: Record<string, any>
  tool_params?: Array<ParamConfig>
  response_extract?: Array<ResponseExtract>
  response_max_chars?: number
  id: number
  user_id: number
  created_at: string
  updated_at: string
}
