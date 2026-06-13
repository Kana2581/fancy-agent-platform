/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
 
export type ScheduledTaskUpdate = {
    agent_id?: (number | null);
    name?: (string | null);
    instruction?: (string | null);
    schedule_type?: ('daily' | 'weekly' | 'monthly' | null);
    schedule_time?: (string | null);
    schedule_day?: (number | null);
    timezone?: (string | null);
    is_enabled?: (boolean | null);
};

