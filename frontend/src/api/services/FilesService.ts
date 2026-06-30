/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Body_upload_file_api_v1_files_post } from '../models/Body_upload_file_api_v1_files_post'
import type { ChatFileResponse } from '../models/ChatFileResponse'
import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'
export class FilesService {
  /**
   * Upload File
   * @param formData
   * @param sessionId
   * @returns ChatFileResponse Successful Response
   * @throws ApiError
   */
  public static uploadFileApiV1FilesPost(
    formData: Body_upload_file_api_v1_files_post,
    sessionId?: number | null
  ): CancelablePromise<ChatFileResponse> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/files',
      query: {
        session_id: sessionId,
      },
      formData: formData,
      mediaType: 'multipart/form-data',
      errors: {
        422: `Validation Error`,
      },
    })
  }
  /**
   * Delete File
   * @param fileId
   * @returns any Successful Response
   * @throws ApiError
   */
  public static deleteFileApiV1FilesFileIdDelete(fileId: number): CancelablePromise<any> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/files/{file_id}',
      path: {
        file_id: fileId,
      },
      errors: {
        422: `Validation Error`,
      },
    })
  }
}
