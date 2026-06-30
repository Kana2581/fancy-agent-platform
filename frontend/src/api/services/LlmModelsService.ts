/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */

import type { LLMCreate } from '../models/LLMCreate'
import type { LLMOut } from '../models/LLMOut'
import type { LLMUpdate } from '../models/LLMUpdate'
import type { LLMTestRequest } from '../models/LLMTestRequest'
import type { LLMTestResult } from '../models/LLMTestResult'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'
export class LlmModelsService {
  /**
   * Create Llm
   * @param requestBody
   * @returns LLMOut Successful Response
   * @throws ApiError
   */
  public static createLlmApiV1LlmPost(requestBody: LLMCreate): CancelablePromise<LLMOut> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/llm',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * List Llms
   * @param offset
   * @param limit
   * @returns LLMOut Successful Response
   * @throws ApiError
   */
  public static listLlmsApiV1LlmGet(
    offset?: number,
    limit: number = 100
  ): CancelablePromise<Array<LLMOut>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/llm',
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
   * Get Llm
   * @param llmId
   * @returns LLMOut Successful Response
   * @throws ApiError
   */
  public static getLlmApiV1LlmLlmIdGet(llmId: number): CancelablePromise<LLMOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/llm/{llm_id}',
      path: {
        llm_id: llmId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Update Llm
   * @param llmId
   * @param requestBody
   * @returns LLMOut Successful Response
   * @throws ApiError
   */
  public static updateLlmApiV1LlmLlmIdPut(
    llmId: number,
    requestBody: LLMUpdate
  ): CancelablePromise<LLMOut> {
    return __request(OpenAPI, {
      method: 'PUT',
      url: '/api/v1/llm/{llm_id}',
      path: {
        llm_id: llmId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Delete Llm
   * @param llmId
   * @returns void
   * @throws ApiError
   */
  /**
   * Test Llm Connection
   * @param requestBody
   * @returns LLMTestResult Successful Response
   * @throws ApiError
   */
  public static testLlmApiV1LlmTestPost(
    requestBody: LLMTestRequest
  ): CancelablePromise<LLMTestResult> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/llm/test',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  public static deleteLlmApiV1LlmLlmIdDelete(llmId: number): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/llm/{llm_id}',
      path: {
        llm_id: llmId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
}
