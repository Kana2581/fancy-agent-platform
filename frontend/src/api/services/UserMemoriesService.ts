import type { UserMemoryOut } from '../models/UserMemoryOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export type UserMemoryCreate = {
    key: string;
    content: string;
    memory_type?: 'core' | 'normal';
    category?: string | null;
};

export class UserMemoriesService {
    public static saveMemory(
        requestBody: UserMemoryCreate,
    ): CancelablePromise<UserMemoryOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/memories',
            body: requestBody,
            mediaType: 'application/json',
            errors: { 422: `Validation Error` },
        });
    }

    public static listMemories(
        memoryType?: 'core' | 'normal',
        category?: string,
    ): CancelablePromise<Array<UserMemoryOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/memories',
            query: { memory_type: memoryType, category },
            errors: { 422: `Validation Error` },
        });
    }

    public static getMemory(key: string): CancelablePromise<UserMemoryOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/memories/{key}',
            path: { key },
            errors: { 422: `Validation Error` },
        });
    }

    public static deleteMemory(key: string): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/memories/{key}',
            path: { key },
            errors: { 422: `Validation Error` },
        });
    }
}
