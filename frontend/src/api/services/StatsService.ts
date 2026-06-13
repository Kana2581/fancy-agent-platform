/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
import type { AgentTokenStatList } from '../models/AgentTokenStatList';
import type { DailyTokenStatList } from '../models/DailyTokenStatList';
import type { TokenSummary } from '../models/TokenSummary';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StatsService {
    /**
     * Get Token Summary
     * @returns TokenSummary Successful Response
     * @throws ApiError
     */
    public static getTokenSummaryApiV1StatsTokensSummaryGet(): CancelablePromise<TokenSummary> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/stats/tokens/summary',
        });
    }
    /**
     * Get Tokens By Agent
     * @returns AgentTokenStatList Successful Response
     * @throws ApiError
     */
    public static getTokensByAgentApiV1StatsTokensByAgentGet(): CancelablePromise<AgentTokenStatList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/stats/tokens/by-agent',
        });
    }
    /**
     * Get Daily Tokens
     * @param days
     * @returns DailyTokenStatList Successful Response
     * @throws ApiError
     */
    public static getDailyTokensApiV1StatsTokensDailyGet(
        days: number = 30,
    ): CancelablePromise<DailyTokenStatList> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/stats/tokens/daily',
            query: {
                'days': days,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    // Short-name aliases
    public static getTokenSummary() {
        return StatsService.getTokenSummaryApiV1StatsTokensSummaryGet();
    }
    public static getTokensByAgent() {
        return StatsService.getTokensByAgentApiV1StatsTokensByAgentGet();
    }
    public static getDailyTokens(days: number = 30) {
        return StatsService.getDailyTokensApiV1StatsTokensDailyGet(days);
    }
}
