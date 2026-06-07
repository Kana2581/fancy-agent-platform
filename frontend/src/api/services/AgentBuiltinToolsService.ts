import type { BuiltinToolInfo } from '../models/BuiltinToolInfo';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class AgentBuiltinToolsService {
    public static listAgentBuiltinToolsApiV1AgentsAgentIdBuiltinToolsGet(
        agentId: number,
    ): CancelablePromise<Array<string>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/agents/{agent_id}/builtin-tools/',
            path: { 'agent_id': agentId },
            errors: { 422: `Validation Error` },
        });
    }

    public static syncAgentBuiltinToolsApiV1AgentsAgentIdBuiltinToolsPost(
        agentId: number,
        requestBody: { tool_types: string[] },
    ): CancelablePromise<Array<string>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/agents/{agent_id}/builtin-tools/',
            path: { 'agent_id': agentId },
            body: requestBody,
            mediaType: 'application/json',
            errors: { 422: `Validation Error` },
        });
    }
}

export class BuiltinToolsService {
    public static listAvailableBuiltinToolsApiV1BuiltinToolsGet(): CancelablePromise<Array<BuiltinToolInfo>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/builtin-tools/',
            errors: { 422: `Validation Error` },
        });
    }
}
