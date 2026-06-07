import type { HelpDocumentOut } from '../models/HelpDocumentOut';
import type { HelpDocumentSummaryOut } from '../models/HelpDocumentSummaryOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

export class HelpDocsService {
  public static listHelpDocuments(
    offset?: number,
    limit: number = 100,
    q?: string,
    category?: string,
    docType?: string,
  ): CancelablePromise<Array<HelpDocumentSummaryOut>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/help-docs',
      query: {
        offset,
        limit,
        q,
        category,
        doc_type: docType,
      },
      errors: {
        422: 'Validation Error',
      },
    });
  }

  public static getHelpDocument(slug: string): CancelablePromise<HelpDocumentOut> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/api/v1/help-docs/{slug}',
      path: {
        slug,
      },
      errors: {
        404: 'Help document not found',
        422: 'Validation Error',
      },
    });
  }
}
