/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SimpleFile } from './SimpleFile';
export type ChatResponse = {
    id: string;
    content: (string | Record<string, any>);
    type: string;
    name?: (string | null);
    parent_id?: (string | null);
    tool_calls?: Array<Record<string, any>> | null;
    files?: (Array<SimpleFile> | null);
    usage_metadata?: (Record<string, any> | null);
    approval_status?: (string | null);
};

