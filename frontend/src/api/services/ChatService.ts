/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApproveToolRequest } from '../models/ApproveToolRequest'
import type { ChatRequest } from '../models/ChatRequest'
import type { ChatResponse } from '../models/ChatResponse'
import type { CompressRequest } from '../models/CompressRequest'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'
export class ChatService {
  /**
   * Chat Stream
   * @param sessionId
   * @param requestBody
   * @returns any Successful Response
   * @throws ApiError
   */
  public static chatStreamApiV1ChatSessionIdStreamPost(
    sessionId: string,
    requestBody: ChatRequest
  ): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/chat/{session_id}/stream',
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
   * Approve Tool
   * @param sessionId
   * @param requestBody
   * @returns any Successful Response
   * @throws ApiError
   */
  public static approveToolApiV1ChatSessionIdApproveToolPost(
    sessionId: string,
    requestBody: ApproveToolRequest
  ): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/chat/{session_id}/approve-tool',
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
   * Get Message Chain To Root
   * @param sessionId
   * @param messageId 起始 message_id，不传则使用 session 最后一条消息
   * @returns ChatResponse Successful Response
   * @throws ApiError
   */
  public static getMessageChainToRootApiV1ChatSessionsSessionIdChainToRootGet(
    sessionId: string,
    messageId?: string | null
  ): CancelablePromise<Array<ChatResponse>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/chat/sessions/{session_id}/chain-to-root',
      path: {
        session_id: sessionId,
      },
      query: {
        message_id: messageId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Get Descendants
   * @param messageId
   * @param sessionId
   * @returns ChatResponse Successful Response
   * @throws ApiError
   */
  public static getDescendantsApiV1ChatMessageIdDescendantsGet(
    messageId: string,
    sessionId: string
  ): CancelablePromise<Array<ChatResponse>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/chat/{message_id}/descendants',
      path: {
        message_id: messageId,
      },
      query: {
        session_id: sessionId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Get Siblings
   * @param messageId
   * @param sessionId
   * @returns ChatResponse Successful Response
   * @throws ApiError
   */
  public static getSiblingsApiV1ChatMessageIdSiblingsGet(
    messageId: string,
    sessionId: string
  ): CancelablePromise<Array<ChatResponse>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/chat/{message_id}/siblings',
      path: {
        message_id: messageId,
      },
      query: {
        session_id: sessionId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Compress Session
   * @param sessionId
   * @param requestBody
   * @returns ChatResponse Successful Response
   * @throws ApiError
   */
  public static compressSessionApiV1ChatSessionIdCompressPost(
    sessionId: string,
    requestBody: CompressRequest
  ): CancelablePromise<ChatResponse> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/chat/{session_id}/compress',
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
   * Export Message Chain
   * @param sessionId
   * @param messageId 导出到该消息为止的祖先链，不传则使用最后一条消息
   * @returns any Successful Response
   * @throws ApiError
   */
  public static exportMessageChainApiV1ChatSessionIdExportGet(
    sessionId: string,
    messageId?: string | null
  ): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/chat/{session_id}/export',
      path: {
        session_id: sessionId,
      },
      query: {
        message_id: messageId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Get Session Messages
   * @param sessionId
   * @returns ChatResponse Successful Response
   * @throws ApiError
   */
  public static getSessionMessagesApiV1ChatSessionIdMessagesGet(
    sessionId: string
  ): CancelablePromise<Array<ChatResponse>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/chat/{session_id}/messages',
      path: {
        session_id: sessionId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
}
