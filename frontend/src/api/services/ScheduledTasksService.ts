/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScheduledTaskCreate } from '../models/ScheduledTaskCreate';
import type { ScheduledTaskExecutionPageOut } from '../models/ScheduledTaskExecutionPageOut';
import type { ScheduledTaskOut } from '../models/ScheduledTaskOut';
import type { ScheduledTaskUpdate } from '../models/ScheduledTaskUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ScheduledTasksService {
    /**
     * List Tasks
     * @returns ScheduledTaskOut Successful Response
     * @throws ApiError
     */
    public static listTasksApiV1ScheduledTasksGet(): CancelablePromise<Array<ScheduledTaskOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/scheduled-tasks',
        });
    }
    /**
     * Create Task
     * @param requestBody
     * @returns ScheduledTaskOut Successful Response
     * @throws ApiError
     */
    public static createTaskApiV1ScheduledTasksPost(
        requestBody: ScheduledTaskCreate,
    ): CancelablePromise<ScheduledTaskOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/scheduled-tasks',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Task
     * @param taskId
     * @param requestBody
     * @returns ScheduledTaskOut Successful Response
     * @throws ApiError
     */
    public static updateTaskApiV1ScheduledTasksTaskIdPut(
        taskId: number,
        requestBody: ScheduledTaskUpdate,
    ): CancelablePromise<ScheduledTaskOut> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/scheduled-tasks/{task_id}',
            path: {
                'task_id': taskId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Task
     * @param taskId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteTaskApiV1ScheduledTasksTaskIdDelete(
        taskId: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/scheduled-tasks/{task_id}',
            path: {
                'task_id': taskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Run Task Now
     * @param taskId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static runTaskNowApiV1ScheduledTasksTaskIdRunPost(
        taskId: number,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/scheduled-tasks/{task_id}/run',
            path: {
                'task_id': taskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Executions
     * @param taskId
     * @param page
     * @param pageSize
     * @returns ScheduledTaskExecutionPageOut Successful Response
     * @throws ApiError
     */
    public static listExecutionsApiV1ScheduledTasksTaskIdExecutionsGet(
        taskId: number,
        page: number = 1,
        pageSize: number = 20,
    ): CancelablePromise<ScheduledTaskExecutionPageOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/scheduled-tasks/{task_id}/executions',
            path: {
                'task_id': taskId,
            },
            query: {
                'page': page,
                'page_size': pageSize,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
