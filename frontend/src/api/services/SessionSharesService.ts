import type {
  SessionShareCreate,
  SessionShareOut,
  SharedSessionView,
} from '../models/SessionShareOut'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'

export class SessionSharesService {
  public static createShare(
    sessionId: string,
    requestBody: SessionShareCreate
  ): CancelablePromise<SessionShareOut> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/sessions/{session_id}/shares',
      path: { session_id: sessionId },
      body: requestBody,
      mediaType: 'application/json',
      errors: { 422: `Validation Error` },
    })
  }

  public static listShares(sessionId: string): CancelablePromise<Array<SessionShareOut>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/sessions/{session_id}/shares',
      path: { session_id: sessionId },
    })
  }

  public static revokeShare(shareId: number): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/session-shares/{share_id}',
      path: { share_id: shareId },
    })
  }

  /** 公开端点：无需鉴权 */
  public static viewShared(slug: string): CancelablePromise<SharedSessionView> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/share/{slug}',
      path: { slug },
    })
  }
}
