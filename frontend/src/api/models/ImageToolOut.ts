/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ImageToolOut = {
    name: string;
    description?: (string | null);
    provider: 'openai' | 'stability' | 'siliconflow' | 'aliyun';
    api_key: string;
    base_url?: (string | null);
    model?: (string | null);
    default_size?: (string | null);
    default_quality?: (string | null);
    default_style?: (string | null);
    extra_params?: (Record<string, any> | null);
    support_img2img?: boolean;
    id: number;
    user_id: number;
    created_at: string;
    updated_at: string;
};

