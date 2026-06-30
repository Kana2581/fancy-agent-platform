import type {
  AgentWebhookCreate,
  AgentWebhookOut,
  AgentWebhookOutWithSecret,
  AgentWebhookUpdate,
} from '../models/AgentWebhookOut'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'

export class AgentWebhooksService {
  public static listWebhooks(): CancelablePromise<Array<AgentWebhookOut>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/agent-webhooks',
    })
  }

  public static createWebhook(
    requestBody: AgentWebhookCreate
  ): CancelablePromise<AgentWebhookOutWithSecret> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/agent-webhooks',
      body: requestBody,
      mediaType: 'application/json',
      errors: { 422: `Validation Error` },
    })
  }

  public static getWebhook(webhookId: number): CancelablePromise<AgentWebhookOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/agent-webhooks/{webhook_id}',
      path: { webhook_id: webhookId },
    })
  }

  public static updateWebhook(
    webhookId: number,
    requestBody: AgentWebhookUpdate
  ): CancelablePromise<AgentWebhookOut> {
    return __request(OpenAPI, {
      method: 'PUT',
      url: '/api/v1/agent-webhooks/{webhook_id}',
      path: { webhook_id: webhookId },
      body: requestBody,
      mediaType: 'application/json',
      errors: { 422: `Validation Error` },
    })
  }

  public static regenerateSecret(webhookId: number): CancelablePromise<AgentWebhookOutWithSecret> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/agent-webhooks/{webhook_id}/regenerate-secret',
      path: { webhook_id: webhookId },
    })
  }

  public static deleteWebhook(webhookId: number): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/agent-webhooks/{webhook_id}',
      path: { webhook_id: webhookId },
    })
  }
}
