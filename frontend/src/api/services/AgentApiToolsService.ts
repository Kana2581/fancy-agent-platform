/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ToolIdsBody } from '../models/ToolIdsBody'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'
export class AgentApiToolsService {
  /**
   * List Agent Tools
   * @param agentId
   * @returns number Successful Response
   * @throws ApiError
   */
  public static listAgentToolsApiV1AgentsAgentIdApiToolsGet(
    agentId: number
  ): CancelablePromise<Array<number>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/agents/{agent_id}/api-tools/',
      path: {
        agent_id: agentId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Sync Agent Tools
   * 同步 agent 绑定的 API 工具（diff 后增删，传空数组则清空）。
   * @param agentId
   * @param requestBody
   * @returns any Successful Response
   * @throws ApiError
   */
  public static syncAgentToolsApiV1AgentsAgentIdApiToolsPost(
    agentId: number,
    requestBody: ToolIdsBody
  ): CancelablePromise<Record<string, any>> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/agents/{agent_id}/api-tools/',
      path: {
        agent_id: agentId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Unbind Agent Tools
   * @param agentId
   * @param requestBody
   * @returns any Successful Response
   * @throws ApiError
   */
  public static unbindAgentToolsApiV1AgentsAgentIdApiToolsDelete(
    agentId: number,
    requestBody: ToolIdsBody
  ): CancelablePromise<Record<string, any>> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/agents/{agent_id}/api-tools/',
      path: {
        agent_id: agentId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
}
