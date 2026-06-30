/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SessionCreate } from '../models/SessionCreate'
import type { SessionOut } from '../models/SessionOut'
import type { SessionPageOut } from '../models/SessionPageOut'
import type { SessionUpdate } from '../models/SessionUpdate'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'
export class SessionsService {
  /**
   * Create Session
   * @param requestBody
   * @returns SessionOut Successful Response
   * @throws ApiError
   */
  public static createSessionApiV1SessionsPost(
    requestBody: SessionCreate
  ): CancelablePromise<SessionOut> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/sessions',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * List Sessions
   * @param agentId
   * @param keyword
   * @param page
   * @param pageSize
   * @returns SessionPageOut Successful Response
   * @throws ApiError
   */
  public static listSessionsApiV1SessionsGet(
    agentId?: number | null,
    keyword?: string | null,
    page: number = 1,
    pageSize: number = 20
  ): CancelablePromise<SessionPageOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/sessions',
      query: {
        agent_id: agentId,
        keyword: keyword,
        page: page,
        page_size: pageSize,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Get Session
   * @param sessionId
   * @returns SessionOut Successful Response
   * @throws ApiError
   */
  public static getSessionApiV1SessionsSessionIdGet(
    sessionId: string
  ): CancelablePromise<SessionOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/sessions/{session_id}',
      path: {
        session_id: sessionId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Update Session
   * @param sessionId
   * @param requestBody
   * @returns SessionOut Successful Response
   * @throws ApiError
   */
  public static updateSessionApiV1SessionsSessionIdPut(
    sessionId: string,
    requestBody: SessionUpdate
  ): CancelablePromise<SessionOut> {
    return __request(OpenAPI, {
      method: 'PUT',
      url: '/api/v1/sessions/{session_id}',
      path: {
        session_id: sessionId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Delete Session
   * @param sessionId
   * @returns any Successful Response
   * @throws ApiError
   */
  public static deleteSessionApiV1SessionsSessionIdDelete(
    sessionId: string
  ): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/sessions/{session_id}',
      path: {
        session_id: sessionId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
}
