import type { SkillFileIn } from './SkillFileIn';
export type SkillCreate = {
    name: string;
    content: string;
    description?: (string | null);
    category?: (string | null);
    scope?: (string | null);
    session_id?: (string | null);
    files?: (Array<SkillFileIn> | null);
};
