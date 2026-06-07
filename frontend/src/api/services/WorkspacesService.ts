/* manually added — pairs with backend app/api/workspace_router.py */
/* tslint:disable */
/* eslint-disable */
import type { WorkspaceFileOut } from '../models/WorkspaceFileOut';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';

function parseFilenameFromContentDisposition(header: string | null, fallback: string): string {
    if (!header) return fallback;
    const utf8Match = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(header);
    if (utf8Match) {
        try {
            return decodeURIComponent(utf8Match[1].trim());
        } catch {
            /* fall through */
        }
    }
    const plainMatch = /filename\s*=\s*"?([^";]+)"?/i.exec(header);
    if (plainMatch) return plainMatch[1].trim();
    return fallback;
}

export class WorkspacesService {
    public static listFiles(sessionId: string): CancelablePromise<Array<WorkspaceFileOut>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/workspace/{session_id}/files',
            path: { session_id: sessionId },
            errors: { 422: `Validation Error` },
        });
    }

    public static deleteFile(sessionId: string, fileId: number): CancelablePromise<void> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/workspace/{session_id}/files/{file_id}',
            path: { session_id: sessionId, file_id: fileId },
            errors: { 422: `Validation Error` },
        });
    }

    public static async downloadFile(
        fileId: number,
        fallbackName: string = `workspace-file-${fileId}`,
    ): Promise<{ blob: Blob; filename: string }> {
        const token = typeof OpenAPI.TOKEN === 'function'
            ? await OpenAPI.TOKEN({ method: 'GET', url: '' } as any)
            : (OpenAPI.TOKEN ?? '');
        const resp = await fetch(`${OpenAPI.BASE}/api/v1/workspace/files/${fileId}/download`, {
            method: 'GET',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            credentials: OpenAPI.WITH_CREDENTIALS ? 'include' : 'same-origin',
        });
        if (!resp.ok) {
            throw new Error(`下载失败 (${resp.status})`);
        }
        const filename = parseFilenameFromContentDisposition(resp.headers.get('Content-Disposition'), fallbackName);
        const blob = await resp.blob();
        return { blob, filename };
    }

    public static async downloadAll(
        sessionId: string,
    ): Promise<{ blob: Blob; filename: string }> {
        const token = typeof OpenAPI.TOKEN === 'function'
            ? await OpenAPI.TOKEN({ method: 'GET', url: '' } as any)
            : (OpenAPI.TOKEN ?? '');
        const resp = await fetch(`${OpenAPI.BASE}/api/v1/workspace/${encodeURIComponent(sessionId)}/download-all`, {
            method: 'GET',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            credentials: OpenAPI.WITH_CREDENTIALS ? 'include' : 'same-origin',
        });
        if (!resp.ok) {
            if (resp.status === 404) {
                throw new Error('没有可打包的文件');
            }
            throw new Error(`打包下载失败 (${resp.status})`);
        }
        const filename = parseFilenameFromContentDisposition(
            resp.headers.get('Content-Disposition'),
            `workspace-${sessionId.slice(0, 8)}.zip`,
        );
        const blob = await resp.blob();
        return { blob, filename };
    }
}
