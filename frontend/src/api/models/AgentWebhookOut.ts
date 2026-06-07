export type AgentWebhookOut = {
    id: number;
    user_id: number;
    agent_id: number;
    name: string;
    slug: string;
    channel: 'generic' | 'telegram' | 'dingtalk' | 'discord';
    discord_public_key?: (string | null);
    enabled: boolean;
    last_triggered_at?: (string | null);
    trigger_count: number;
    created_at: string;
    updated_at: string;
};

export type AgentWebhookOutWithSecret = AgentWebhookOut & {
    secret: string;
};

export type AgentWebhookCreate = {
    agent_id: number;
    name: string;
    channel?: 'generic' | 'telegram' | 'dingtalk' | 'discord';
    telegram_bot_token?: (string | null);
    dingtalk_app_secret?: (string | null);
    discord_public_key?: (string | null);
};

export type AgentWebhookUpdate = {
    name?: (string | null);
    agent_id?: (number | null);
    enabled?: (boolean | null);
    telegram_bot_token?: (string | null);
    dingtalk_app_secret?: (string | null);
    discord_public_key?: (string | null);
};
