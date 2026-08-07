import type { CancelablePromise } from '../core/CancelablePromise'
import { OpenAPI } from '../core/OpenAPI'
import { request as __request } from '../core/request'
import type {
  StructuredOutputSchemaInput,
  StructuredOutputSchemaOut,
} from '../models/StructuredOutputSchema'

export class StructuredOutputSchemasService {
  public static create(requestBody: StructuredOutputSchemaInput): CancelablePromise<StructuredOutputSchemaOut> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/api/v1/structured-output-schemas',
      body: requestBody,
      mediaType: 'application/json',
    })
  }

  public static list(): CancelablePromise<StructuredOutputSchemaOut[]> {
    return __request(OpenAPI, { method: 'GET', url: '/api/v1/structured-output-schemas' })
  }

  public static get(schemaId: number): CancelablePromise<StructuredOutputSchemaOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/structured-output-schemas/{schema_id}',
      path: { schema_id: schemaId },
    })
  }

  public static update(
    schemaId: number,
    requestBody: StructuredOutputSchemaInput
  ): CancelablePromise<StructuredOutputSchemaOut> {
    return __request(OpenAPI, {
      method: 'PUT',
      url: '/api/v1/structured-output-schemas/{schema_id}',
      path: { schema_id: schemaId },
      body: requestBody,
      mediaType: 'application/json',
    })
  }

  public static delete(schemaId: number): CancelablePromise<void> {
    return __request(OpenAPI, {
      method: 'DELETE',
      url: '/api/v1/structured-output-schemas/{schema_id}',
      path: { schema_id: schemaId },
    })
  }
}
