/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AgentCreate } from '../models/AgentCreate';
import type { AgentFullOut } from '../models/AgentFullOut';
import type { AgentOut } from '../models/AgentOut';
import type { AgentUpdate } from '../models/AgentUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AgentsService {
    /**
     * Get Agent
     * @param agentId
     * @returns AgentFullOut Successful Response
     * @throws ApiError
     */
    public static getAgentApiV1AgentsAgentIdGet(
        agentId: number,
    ): CancelablePromise<AgentFullOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/agents/{agent_id}',
            path: {
                'agent_id': agentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Agent
     * @param agentId
     * @param requestBody
     * @returns AgentOut Successful Response
     * @throws ApiError
     */
    public static updateAgentApiV1AgentsAgentIdPut(
        agentId: number,
        requestBody: AgentUpdate,
    ): CancelablePromise<AgentOut> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/agents/{agent_id}',
            path: {
                'agent_id': agentId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Agent
     * @param agentId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteAgentApiV1AgentsAgentIdDelete(
        agentId: number,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/agents/{agent_id}',
            path: {
                'agent_id': agentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Agents
     * @param offset
     * @param limit
     * @returns AgentOut Successful Response
     * @throws ApiError
     */
    public static listAgentsApiV1AgentsGet(
        offset?: number,
        limit: number = 100,
    ): CancelablePromise<Array<AgentOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/agents/',
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
     * Create Agent
     * @param requestBody
     * @returns AgentOut Successful Response
     * @throws ApiError
     */
    public static createAgentApiV1AgentsPost(
        requestBody: AgentCreate,
    ): CancelablePromise<AgentOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/agents/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
