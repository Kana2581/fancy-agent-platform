BUILTIN_TOOL_WEB_SEARCH = "web_search"
BUILTIN_TOOL_WEB_FETCH = "web_fetch"
BUILTIN_TOOL_PYTHON_EXEC = "python_exec"
BUILTIN_TOOL_SCHEDULED_TASK_MANAGER = "scheduled_task_manager"
BUILTIN_TOOL_SKILL_MANAGER = "skill_manager"
BUILTIN_TOOL_MEMORY_MANAGER = "memory_manager"
BUILTIN_TOOL_PROMPT_TEMPLATE_MANAGER = "prompt_template_manager"
BUILTIN_TOOL_KNOWLEDGE_GRAPH_MANAGER = "knowledge_graph_manager"
BUILTIN_TOOL_HELP_DOCUMENT_MANAGER = "help_document_manager"
BUILTIN_TOOL_WORKSPACE_MANAGER = "workspace_manager"

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
        "tool_type": "python_exec",
        "name": "Python 执行",
        "description": "执行 Python 代码，支持 matplotlib 图表生成，输出文件以 URL 返回",
    },
    {
        "tool_type": "scheduled_task_manager",
        "name": "定时任务管理",
        "description": "查看、创建、修改定时任务（list_scheduled_tasks / create_scheduled_task / update_scheduled_task）",
    },
    {
        "tool_type": "skill_manager",
        "name": "技能管理",
        "description": "查看、创建、修改、使用技能（list_my_skills / get_skill / create_skill / update_skill）",
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
    {
        "tool_type": "workspace_manager",
        "name": "工作区文件",
        "description": "在 session 工作区内读写文件并向用户呈现下载（ws_list / ws_read / ws_write / ws_edit / ws_delete / ws_present / uploads_list / uploads_read）。需要 session 上下文",
    },
]

VALID_BUILTIN_TOOL_TYPES = {t["tool_type"] for t in BUILTIN_TOOL_CATALOG}
