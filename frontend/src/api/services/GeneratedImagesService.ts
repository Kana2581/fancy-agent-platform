/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
import type { GeneratedImageOut } from '../models/GeneratedImageOut';
import type { GeneratedImagePageOut } from '../models/GeneratedImagePageOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class GeneratedImagesService {
    /**
     * List Generated Images
     * @param page
     * @param pageSize
     * @returns GeneratedImagePageOut Successful Response
     * @throws ApiError
     */
    public static listGeneratedImagesApiV1GeneratedImagesGet(
        page: number = 1,
        pageSize: number = 20,
    ): CancelablePromise<GeneratedImagePageOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/generated-images',
            query: {
                'page': page,
                'page_size': pageSize,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Generated Image
     * @param recordId
     * @returns GeneratedImageOut Successful Response
     * @throws ApiError
     */
    public static getGeneratedImageApiV1GeneratedImagesRecordIdGet(
        recordId: number,
    ): CancelablePromise<GeneratedImageOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/generated-images/{record_id}',
            path: {
                'record_id': recordId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Generated Image
     * @param recordId
     * @returns void
     * @throws ApiError
     */
    public static deleteGeneratedImageApiV1GeneratedImagesRecordIdDelete(
        recordId: number,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/generated-images/{record_id}',
            path: {
                'record_id': recordId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
