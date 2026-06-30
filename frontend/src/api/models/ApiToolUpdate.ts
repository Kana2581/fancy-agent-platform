/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ParamConfig } from './ParamConfig'
import type { ResponseExtract } from './ResponseExtract'
export type ApiToolUpdate = {
  name?: string | null
  description?: string | null
  url?: string | null
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | null
  headers?: Record<string, string> | null
  param_location?: 'query' | 'body' | 'path_and_query' | 'path_and_body' | null
  fixed_params?: Record<string, any> | null
  tool_params?: Array<ParamConfig> | null
  response_extract?: Array<ResponseExtract> | null
  response_max_chars?: number | null
}
