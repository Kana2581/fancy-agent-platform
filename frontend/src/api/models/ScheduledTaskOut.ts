/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ScheduledTaskOut = {
    id: number;
    user_id: number;
    agent_id: number;
    name: string;
    instruction: string;
    schedule_type: string;
    schedule_time: string;
    schedule_day: (number | null);
    timezone: string;
    is_enabled: boolean;
    last_run_at: (string | null);
    next_run_at: (string | null);
    created_at: string;
    updated_at: string;
};

