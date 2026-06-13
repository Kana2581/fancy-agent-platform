/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
export type schedule_type = 'daily' | 'weekly' | 'monthly';
export const schedule_type = {
    DAILY: 'daily' as schedule_type,
    WEEKLY: 'weekly' as schedule_type,
    MONTHLY: 'monthly' as schedule_type,
};
export type ScheduledTaskCreate = {
    agent_id: number;
    name: string;
    instruction: string;
    schedule_type: schedule_type;
    schedule_time: string;
    schedule_day?: (number | null);
    timezone?: string;
};

