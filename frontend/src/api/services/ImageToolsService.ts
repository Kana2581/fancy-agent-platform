/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_img2img_api_v1_image_tools__tool_id__img2img_post } from '../models/Body_img2img_api_v1_image_tools__tool_id__img2img_post'
import type { GenerateRequest } from '../models/GenerateRequest'
import type { GenerateResponse } from '../models/GenerateResponse'
import type { ImageToolCreate } from '../models/ImageToolCreate'
import type { ImageToolOut } from '../models/ImageToolOut'
import type { ImageToolUpdate } from '../models/ImageToolUpdate'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'

export type Img2ImgRefRequest = {
  prompt: string
  image_url?: string | null
  object_key?: string | null
  negative_prompt?: string
  width?: number
  height?: number
  extra?: Record<string, any>
}

export class ImageToolsService {
  /**
   * Create Image Tool
   * @param requestBody
   * @returns ImageToolOut Successful Response
   * @throws ApiError
   */
  public static createImageToolApiV1ImageToolsPost(
    requestBody: ImageToolCreate
  ): CancelablePromise<ImageToolOut> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/image-tools',
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * List Image Tools
   * @param offset
   * @param limit
   * @returns ImageToolOut Successful Response
   * @throws ApiError
   */
  public static listImageToolsApiV1ImageToolsGet(
    offset?: number,
    limit: number = 100
  ): CancelablePromise<Array<ImageToolOut>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/image-tools',
      query: {
        offset: offset,
        limit: limit,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Get Image Tool
   * @param toolId
   * @returns ImageToolOut Successful Response
   * @throws ApiError
   */
  public static getImageToolApiV1ImageToolsToolIdGet(
    toolId: number
  ): CancelablePromise<ImageToolOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/image-tools/{tool_id}',
      path: {
        tool_id: toolId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Update Image Tool
   * @param toolId
   * @param requestBody
   * @returns ImageToolOut Successful Response
   * @throws ApiError
   */
  public static updateImageToolApiV1ImageToolsToolIdPut(
    toolId: number,
    requestBody: ImageToolUpdate
  ): CancelablePromise<ImageToolOut> {
    return __request(OpenAPI, {
      method: 'PUT',
      url: '/api/v1/image-tools/{tool_id}',
      path: {
        tool_id: toolId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Delete Image Tool
   * @param toolId
   * @returns void
   * @throws ApiError
   */
  public static deleteImageToolApiV1ImageToolsToolIdDelete(
    toolId: number
  ): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/image-tools/{tool_id}',
      path: {
        tool_id: toolId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Generate Image
   * @param toolId
   * @param requestBody
   * @returns GenerateResponse Successful Response
   * @throws ApiError
   */
  public static generateImageApiV1ImageToolsToolIdGeneratePost(
    toolId: number,
    requestBody: GenerateRequest
  ): CancelablePromise<GenerateResponse> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/image-tools/{tool_id}/generate',
      path: {
        tool_id: toolId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Img2Img
   * @param toolId
   * @param formData
   * @returns GenerateResponse Successful Response
   * @throws ApiError
   */
  public static img2ImgApiV1ImageToolsToolIdImg2ImgPost(
    toolId: number,
    formData: Body_img2img_api_v1_image_tools__tool_id__img2img_post
  ): CancelablePromise<GenerateResponse> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/image-tools/{tool_id}/img2img',
      path: {
        tool_id: toolId,
      },
      formData: formData,
      mediaType: 'multipart/form-data',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Img2Img By Reference
   * @param toolId
   * @param requestBody
   * @returns GenerateResponse Successful Response
   * @throws ApiError
   */
  public static img2ImgByReferenceApiV1ImageToolsToolIdImg2ImgRefPost(
    toolId: number,
    requestBody: Img2ImgRefRequest
  ): CancelablePromise<GenerateResponse> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/image-tools/{tool_id}/img2img/ref',
      path: {
        tool_id: toolId,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    })
  }

  // Short-name aliases
  public static listImageTools(offset?: number, limit: number = 100) {
    return ImageToolsService.listImageToolsApiV1ImageToolsGet(offset, limit)
  }
  public static createImageTool(requestBody: ImageToolCreate) {
    return ImageToolsService.createImageToolApiV1ImageToolsPost(requestBody)
  }
  public static updateImageTool(toolId: number, requestBody: ImageToolUpdate) {
    return ImageToolsService.updateImageToolApiV1ImageToolsToolIdPut(toolId, requestBody)
  }
  public static deleteImageTool(toolId: number) {
    return ImageToolsService.deleteImageToolApiV1ImageToolsToolIdDelete(toolId)
  }
  public static generateImage(toolId: number, requestBody: GenerateRequest) {
    return ImageToolsService.generateImageApiV1ImageToolsToolIdGeneratePost(toolId, requestBody)
  }
  public static img2ImgByReference(toolId: number, requestBody: Img2ImgRefRequest) {
    return ImageToolsService.img2ImgByReferenceApiV1ImageToolsToolIdImg2ImgRefPost(
      toolId,
      requestBody
    )
  }
}
