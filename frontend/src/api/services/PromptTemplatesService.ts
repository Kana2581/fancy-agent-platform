import type { PromptTemplateCreate } from '../models/PromptTemplateCreate';
import type { PromptTemplateOut } from '../models/PromptTemplateOut';
import type { PromptTemplateUpdate } from '../models/PromptTemplateUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class PromptTemplatesService {
    public static createPromptTemplate(
        requestBody: PromptTemplateCreate,
    ): CancelablePromise<PromptTemplateOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/prompt-templates',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    public static listPromptTemplates(
        offset?: number,
        limit: number = 100,
        category?: string,
    ): CancelablePromise<Array<PromptTemplateOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/prompt-templates',
            query: {
                'offset': offset,
                'limit': limit,
                'category': category,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    public static getPromptTemplate(
        templateId: number,
    ): CancelablePromise<PromptTemplateOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/prompt-templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    public static updatePromptTemplate(
        templateId: number,
        requestBody: PromptTemplateUpdate,
    ): CancelablePromise<PromptTemplateOut> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/prompt-templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    public static deletePromptTemplate(
        templateId: number,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/prompt-templates/{template_id}',
            path: {
                'template_id': templateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
