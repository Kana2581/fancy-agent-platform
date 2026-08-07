import type { SkillFileContentOut } from '../models/SkillFileContentOut'
import type { SkillOut } from '../models/SkillOut'
import type { SkillTreeNode } from '../models/SkillTreeNode'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'

export class SkillsService {
  public static listSkills(scope: 'all' | 'user' | 'system' = 'all'): CancelablePromise<Array<SkillOut>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/skills',
      query: { scope },
    })
  }

  public static listTree(scope: 'user' | 'system', packagePath: string): CancelablePromise<Array<SkillTreeNode>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/skills/tree',
      query: { scope, package_path: packagePath },
    })
  }

  public static readFile(
    scope: 'user' | 'system',
    packagePath: string,
    path: string
  ): CancelablePromise<SkillFileContentOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/skills/file',
      query: { scope, package_path: packagePath, path },
    })
  }
}
