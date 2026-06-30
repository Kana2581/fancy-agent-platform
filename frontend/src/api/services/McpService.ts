/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */

import type { MCPCreate } from '../models/MCPCreate'
import type { MCPOut } from '../models/MCPOut'
import type { MCPUpdate } from '../models/MCPUpdate'
import type { ToolOut } from '../models/ToolOut'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'
export class McpService {
  /**
   * Create Mcp
   * @param requestBody
   * @returns MCPOut Successful Response
   * @throws ApiError
   */
  public static createMcpApiV1McpsPost(requestBody: MCPCreate): CancelablePromise<MCPOut> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/mcps',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * List Mcps
   * @param offset
   * @param limit
   * @returns MCPOut Successful Response
   * @throws ApiError
   */
  public static listMcpsApiV1McpsGet(
    offset?: number,
    limit: number = 100
  ): CancelablePromise<Array<MCPOut>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/mcps',
      query: {
        offset: offset,
        limit: limit,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Get Mcp
   * @param mcpId
   * @returns MCPOut Successful Response
   * @throws ApiError
   */
  public static getMcpApiV1McpsMcpIdGet(mcpId: number): CancelablePromise<MCPOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/mcps/{mcp_id}',
      path: {
        mcp_id: mcpId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Update Mcp
   * @param mcpId
   * @param requestBody
   * @returns MCPOut Successful Response
   * @throws ApiError
   */
  public static updateMcpApiV1McpsMcpIdPut(
    mcpId: number,
    requestBody: MCPUpdate
  ): CancelablePromise<MCPOut> {
    return __request(OpenAPI, {
      method: 'PUT',
      url: '/api/v1/mcps/{mcp_id}',
      path: {
        mcp_id: mcpId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Delete Mcp
   * @param mcpId
   * @returns void
   * @throws ApiError
   */
  public static deleteMcpApiV1McpsMcpIdDelete(mcpId: number): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/mcps/{mcp_id}',
      path: {
        mcp_id: mcpId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Get Mcp Tools
   * @param mcpId
   * @returns ToolOut Successful Response
   * @throws ApiError
   */
  public static getMcpToolsApiV1McpsMcpIdToolsGet(
    mcpId: number
  ): CancelablePromise<Array<ToolOut>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/mcps/{mcp_id}/tools',
      path: {
        mcp_id: mcpId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
}
