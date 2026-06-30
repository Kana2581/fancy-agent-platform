/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'
export class AgentMcpsService {
  /**
   * List Mcps
   * @param agentId
   * @returns number Successful Response
   * @throws ApiError
   */
  public static listMcpsApiV1AgentsAgentIdMcpsGet(
    agentId: number
  ): CancelablePromise<Array<number>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/agents/{agent_id}/mcps/',
      path: {
        agent_id: agentId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Bind Mcps
   * @param agentId
   * @param requestBody
   * @returns number Successful Response
   * @throws ApiError
   */
  public static bindMcpsApiV1AgentsAgentIdMcpsPost(
    agentId: number,
    requestBody?: Array<number>
  ): CancelablePromise<Array<number>> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/agents/{agent_id}/mcps/',
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
   * Unbind Mcps
   * @param agentId
   * @param requestBody
   * @returns any Successful Response
   * @throws ApiError
   */
  public static unbindMcpsApiV1AgentsAgentIdMcpsDelete(
    agentId: number,
    requestBody?: Array<number>
  ): CancelablePromise<Record<string, any>> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/agents/{agent_id}/mcps/',
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
