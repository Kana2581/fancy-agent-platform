/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ToolIdsBody } from '../models/ToolIdsBody'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'
export class AgentImageToolsService {
  /**
   * List Agent Image Tools
   * @param agentId
   * @returns number Successful Response
   * @throws ApiError
   */
  public static listAgentImageToolsApiV1AgentsAgentIdImageToolsGet(
    agentId: number
  ): CancelablePromise<Array<number>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/agents/{agent_id}/image-tools/',
      path: {
        agent_id: agentId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Sync Agent Image Tools
   * 同步 agent 绑定的图像生成工具（diff 后增删，传空数组则清空）。
   * @param agentId
   * @param requestBody
   * @returns any Successful Response
   * @throws ApiError
   */
  public static syncAgentImageToolsApiV1AgentsAgentIdImageToolsPost(
    agentId: number,
    requestBody: ToolIdsBody
  ): CancelablePromise<Record<string, any>> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/agents/{agent_id}/image-tools/',
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
   * Unbind Agent Image Tools
   * @param agentId
   * @param requestBody
   * @returns any Successful Response
   * @throws ApiError
   */
  public static unbindAgentImageToolsApiV1AgentsAgentIdImageToolsDelete(
    agentId: number,
    requestBody: ToolIdsBody
  ): CancelablePromise<Record<string, any>> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/agents/{agent_id}/image-tools/',
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
