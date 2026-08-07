BUILTIN_TOOL_WEB_SEARCH = "web_search"
BUILTIN_TOOL_WEB_FETCH = "web_fetch"
BUILTIN_TOOL_SANDBOX = "sandbox"
BUILTIN_TOOL_PYTHON_EXEC = "python_exec"
BUILTIN_TOOL_BASH_EXEC = "bash_exec"
BUILTIN_TOOL_SCHEDULED_TASK_MANAGER = "scheduled_task_manager"
BUILTIN_TOOL_MEMORY_MANAGER = "memory_manager"
BUILTIN_TOOL_PROMPT_TEMPLATE_MANAGER = "prompt_template_manager"
BUILTIN_TOOL_KNOWLEDGE_GRAPH_MANAGER = "knowledge_graph_manager"
BUILTIN_TOOL_HELP_DOCUMENT_MANAGER = "help_document_manager"
BUILTIN_TOOL_WORKSPACE_MANAGER = "workspace_manager"

# These values may still exist in persisted rows from older deployments. They
# are accepted by the runtime and folded into the unified sandbox tool.
LEGACY_SANDBOX_TOOL_TYPES = {
    BUILTIN_TOOL_PYTHON_EXEC,
    BUILTIN_TOOL_BASH_EXEC,
    BUILTIN_TOOL_WORKSPACE_MANAGER,
    "skill_manager",
}

BUILTIN_TOOL_CATALOG = [
    {
        "tool_type": "web_search",
        "name": "网络搜索",
        "description": "搜索实时网络信息（Tavily/DuckDuckGo）",
    },
    {
        "tool_type": "web_fetch",
        "name": "网页抓取",
        "description": "抓取指定 URL 的网页正文内容",
    },
    {
        "tool_type": BUILTIN_TOOL_SANDBOX,
        "name": "会话沙箱",
        "description": "在隔离环境中执行 Bash，操作会话工作区和文件系统 Skill",
    },
    {
        "tool_type": "scheduled_task_manager",
        "name": "定时任务管理",
        "description": "查看、创建、修改定时任务（list_scheduled_tasks / create_scheduled_task / update_scheduled_task）",
    },
    {
        "tool_type": "memory_manager",
        "name": "记忆管理",
        "description": "存取用户长期记忆（save_memory / get_memory / list_memories / delete_memory）；core 级记忆自动注入系统提示词",
    },
    {
        "tool_type": "prompt_template_manager",
        "name": "提示词模板管理",
        "description": "增删改查提示词模板（list_prompt_templates / get_prompt_template / create_prompt_template / update_prompt_template / delete_prompt_template）",
    },
    {
        "tool_type": "knowledge_graph_manager",
        "name": "知识图谱管理",
        "description": "从文本自动提取并存储知识图谱（kg_extract_and_save），以及手动增删查节点和关系（kg_add_node / kg_add_edge / kg_search_nodes / kg_get_neighbors / kg_delete_node）",
    },
    {
        "tool_type": "help_document_manager",
        "name": "帮助文档管理",
        "description": "检索平台帮助文档（list_help_documents / get_help_document），用于回答 Fancy Agent 功能和配置问题",
    },
]

VALID_BUILTIN_TOOL_TYPES = {t["tool_type"] for t in BUILTIN_TOOL_CATALOG}
VALID_BUILTIN_TOOL_TYPES_WITH_LEGACY = VALID_BUILTIN_TOOL_TYPES | LEGACY_SANDBOX_TOOL_TYPES
