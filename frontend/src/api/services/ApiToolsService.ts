/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiToolCreate } from '../models/ApiToolCreate';
import type { ApiToolOut } from '../models/ApiToolOut';
import type { ApiToolUpdate } from '../models/ApiToolUpdate';
import type { TestRequest } from '../models/TestRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ApiToolsService {
    /**
     * Create Api Tool
     * @param requestBody
     * @returns ApiToolOut Successful Response
     * @throws ApiError
     */
    public static createApiToolApiV1ApiToolsPost(
        requestBody: ApiToolCreate,
    ): CancelablePromise<ApiToolOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/api-tools',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Api Tools
     * @param offset
     * @param limit
     * @returns ApiToolOut Successful Response
     * @throws ApiError
     */
    public static listApiToolsApiV1ApiToolsGet(
        offset?: number,
        limit: number = 100,
    ): CancelablePromise<Array<ApiToolOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/api-tools',
            query: {
                'offset': offset,
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Api Tool
     * @param toolId
     * @returns ApiToolOut Successful Response
     * @throws ApiError
     */
    public static getApiToolApiV1ApiToolsToolIdGet(
        toolId: number,
    ): CancelablePromise<ApiToolOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/api-tools/{tool_id}',
            path: {
                'tool_id': toolId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Api Tool
     * @param toolId
     * @param requestBody
     * @returns ApiToolOut Successful Response
     * @throws ApiError
     */
    public static updateApiToolApiV1ApiToolsToolIdPut(
        toolId: number,
        requestBody: ApiToolUpdate,
    ): CancelablePromise<ApiToolOut> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/api-tools/{tool_id}',
            path: {
                'tool_id': toolId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Api Tool
     * @param toolId
     * @returns void
     * @throws ApiError
     */
    public static deleteApiToolApiV1ApiToolsToolIdDelete(
        toolId: number,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/api-tools/{tool_id}',
            path: {
                'tool_id': toolId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Test Api Tool
     * @param toolId
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static testApiToolApiV1ApiToolsToolIdTestPost(
        toolId: number,
        requestBody: TestRequest,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/api-tools/{tool_id}/test',
            path: {
                'tool_id': toolId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
