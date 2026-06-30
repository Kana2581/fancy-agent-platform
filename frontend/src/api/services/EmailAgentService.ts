/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserEmailAgentCreate } from '../models/UserEmailAgentCreate'
import type { UserEmailAgentOut } from '../models/UserEmailAgentOut'
import type { UserEmailAgentUpdate } from '../models/UserEmailAgentUpdate'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'
export class EmailAgentService {
  /**
   * Get Email Agent
   * @returns UserEmailAgentOut Successful Response
   * @throws ApiError
   */
  public static getEmailAgentApiV1EmailAgentGet(): CancelablePromise<UserEmailAgentOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/email-agent',
    })
  }
  /**
   * Update Email Agent
   * @param requestBody
   * @returns UserEmailAgentOut Successful Response
   * @throws ApiError
   */
  public static updateEmailAgentApiV1EmailAgentPut(
    requestBody: UserEmailAgentUpdate
  ): CancelablePromise<UserEmailAgentOut> {
    return __request(OpenAPI, {
      method: 'PUT',
      url: '/api/v1/email-agent',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Create Email Agent
   * @param requestBody
   * @returns UserEmailAgentOut Successful Response
   * @throws ApiError
   */
  public static createEmailAgentApiV1EmailAgentPost(
    requestBody: UserEmailAgentCreate
  ): CancelablePromise<UserEmailAgentOut> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/email-agent',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Delete Email Agent
   * @returns any Successful Response
   * @throws ApiError
   */
  public static deleteEmailAgentApiV1EmailAgentDelete(): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/email-agent',
    })
  }
}
