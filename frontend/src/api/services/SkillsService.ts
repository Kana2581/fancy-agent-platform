import type { SkillCreate } from '../models/SkillCreate';
import type { SkillOut } from '../models/SkillOut';
import type { SkillUpdate } from '../models/SkillUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class SkillsService {
    public static createSkill(
        requestBody: SkillCreate,
    ): CancelablePromise<SkillOut> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/skills',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    public static listSkills(
        offset?: number,
        limit: number = 100,
        category?: string,
        scope?: string,
    ): CancelablePromise<Array<SkillOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/skills',
            query: {
                'offset': offset,
                'limit': limit,
                'category': category,
                'scope': scope,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    public static getSkill(
        skillId: number,
    ): CancelablePromise<SkillOut> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/skills/{skill_id}',
            path: {
                'skill_id': skillId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }

    public static updateSkill(
        skillId: number,
        requestBody: SkillUpdate,
    ): CancelablePromise<SkillOut> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/skills/{skill_id}',
            path: {
                'skill_id': skillId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }

    public static deleteSkill(
        skillId: number,
    ): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/skills/{skill_id}',
            path: {
                'skill_id': skillId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
