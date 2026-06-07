import json
from typing import List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.deps.db import get_db_session
from app.mappers.skill_file_mapper import SkillFileMapper
from app.mappers.skill_mapper import SkillMapper
from app.models.skill import SKILL_SCOPE_SESSION, SKILL_SCOPE_SYSTEM, SKILL_SCOPE_USER
from app.schemas.skill_schema import SkillUpdate
from app.services.skill_service import SkillService
from app.utils.workspace_path import PathTraversalError, ensure_workspace, safe_resolve


class ListMySkillsInput(BaseModel):
    category: Optional[str] = Field(default=None, description="按分类过滤，不填则返回全部")


class GetSkillInput(BaseModel):
    name: str = Field(description="要查看的技能名称")


class UseSkillInput(BaseModel):
    name: str = Field(description="要启用的技能名称")


class CreateSkillInput(BaseModel):
    name: str = Field(description="技能名称，需唯一")
    content: str = Field(description="技能的完整内容（如提示词、操作步骤、代码等）")
    description: Optional[str] = Field(default=None, description="技能的简短描述")
    category: Optional[str] = Field(default=None, description="分类标签，可选")
    scope: Optional[str] = Field(
        default=None,
        description="user(默认，跨会话持久) 或 session(仅当前会话有效，会话结束被清理)",
    )


class UpdateSkillInput(BaseModel):
    skill_id: int = Field(description="要修改的技能 ID")
    name: Optional[str] = Field(default=None, description="新名称")
    content: Optional[str] = Field(default=None, description="新内容")
    description: Optional[str] = Field(default=None, description="新描述")
    category: Optional[str] = Field(default=None, description="新分类")


def build_skill_manager_tools(user_id: int, session_id: Optional[str] = None) -> List[BaseTool]:
    class ListMySkillsTool(BaseTool):
        name: str = "list_my_skills"
        description: str = (
            "列出当前可用的技能（包含平台内置 + 用户自建 + 当前会话临时）。"
            "返回 [{id, name, description, category, scope}]，scope 标识技能来源。"
        )
        args_schema: Type[BaseModel] = ListMySkillsInput

        async def _arun(self, category: Optional[str] = None) -> str:
            async with get_db_session() as db:
                skills = await SkillService(db).list_layered(
                    user_id, session_id=session_id, category=category
                )
                return json.dumps(
                    [
                        {
                            "id": s.id,
                            "name": s.name,
                            "description": s.description or "",
                            "category": s.category or "",
                            "scope": s.scope,
                        }
                        for s in skills
                    ],
                    ensure_ascii=False,
                )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class GetSkillTool(BaseTool):
        name: str = "get_skill"
        description: str = (
            "按名称查看技能完整内容。"
            "同名优先返回 session > user > system 层级。"
            "若技能附带脚本/文件，会列出文件清单（仅路径），用 use_skill 物化后即可运行。"
        )
        args_schema: Type[BaseModel] = GetSkillInput

        async def _arun(self, name: str) -> str:
            async with get_db_session() as db:
                skill = await SkillMapper(db).get_by_name(user_id, name, session_id=session_id)
                if not skill:
                    return f"未找到名为「{name}」的技能，请先调用 list_my_skills 查看可用技能。"
                files = await SkillFileMapper(db).list_by_skill(skill.id)
                if not files:
                    return skill.content
                manifest = "\n".join(f"- {f.path}" for f in files)
                return (
                    f"{skill.content}\n\n---\n本技能附带以下文件（调用 use_skill(\"{name}\") "
                    f"物化到工作区后用 python_exec 运行）：\n{manifest}"
                )

        def _run(self, name: str) -> str:
            raise NotImplementedError("Use async version")

    class UseSkillTool(BaseTool):
        name: str = "use_skill"
        description: str = (
            "启用一个技能：把它附带的脚本/文件物化到当前会话工作区的 .skills/<name>/ 下，"
            "并返回技能说明 + 物化出来的文件清单。"
            "随后用 python_exec(script='.skills/<name>/xxx.py') 运行其中的脚本（脚本只能用预装库）。"
            "无附带文件的技能等价于 get_skill。"
        )
        args_schema: Type[BaseModel] = UseSkillInput

        async def _arun(self, name: str) -> str:
            if not session_id:
                return json.dumps({"error": "当前上下文无 session_id，无法物化技能文件"}, ensure_ascii=False)
            async with get_db_session() as db:
                skill = await SkillMapper(db).get_by_name(user_id, name, session_id=session_id)
                if not skill:
                    return json.dumps(
                        {"error": f"未找到名为「{name}」的技能，请先 list_my_skills"},
                        ensure_ascii=False,
                    )
                files = await SkillFileMapper(db).list_by_skill(skill.id)

            ensure_workspace(user_id, session_id)
            materialized: List[str] = []
            runnable: List[str] = []
            for f in files:
                try:
                    target = safe_resolve(user_id, session_id, f".skills/{name}/{f.path}")
                except PathTraversalError:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f.content, encoding="utf-8")
                rel = f".skills/{name}/{f.path}"
                materialized.append(rel)
                if f.path.lower().endswith(".py"):
                    runnable.append(rel)

            return json.dumps(
                {
                    "content": skill.content,
                    "files": materialized,
                    "runnable": runnable,
                    "hint": (
                        "用 python_exec(script='<runnable 里的路径>') 运行脚本；"
                        "其它文件可用 ws_read 查看或在脚本里读取。"
                    ) if materialized else "本技能无附带文件，按 content 说明操作即可。",
                },
                ensure_ascii=False,
            )

        def _run(self, name: str) -> str:
            raise NotImplementedError("Use async version")

    class CreateSkillTool(BaseTool):
        name: str = "create_skill"
        description: str = (
            "创建一个新技能。scope=user (默认，跨会话保留) 或 session (仅当前会话临时)。"
            "禁止创建 system 级技能。"
        )
        args_schema: Type[BaseModel] = CreateSkillInput

        async def _arun(
            self,
            name: str,
            content: str,
            description: Optional[str] = None,
            category: Optional[str] = None,
            scope: Optional[str] = None,
        ) -> str:
            effective_scope = scope or SKILL_SCOPE_USER
            if effective_scope == SKILL_SCOPE_SESSION and not session_id:
                return json.dumps({"error": "当前上下文无 session_id，无法创建 session 级技能"}, ensure_ascii=False)
            if effective_scope not in (SKILL_SCOPE_USER, SKILL_SCOPE_SESSION):
                return json.dumps({"error": f"scope 只能是 user/session，禁止 {effective_scope}"}, ensure_ascii=False)

            async with get_db_session() as db:
                try:
                    skill = await SkillService(db).create_skill(
                        {
                            "user_id": user_id,
                            "name": name,
                            "content": content,
                            "description": description,
                            "category": category,
                            "scope": effective_scope,
                            "session_id": session_id if effective_scope == SKILL_SCOPE_SESSION else "",
                        }
                    )
                except ValueError as e:
                    return json.dumps({"error": str(e)}, ensure_ascii=False)
                return json.dumps(
                    {"id": skill.id, "name": skill.name, "scope": skill.scope},
                    ensure_ascii=False,
                )

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    class UpdateSkillTool(BaseTool):
        name: str = "update_skill"
        description: str = "修改已有用户/会话技能的名称、内容、描述或分类。无权修改 system 级技能。"
        args_schema: Type[BaseModel] = UpdateSkillInput

        async def _arun(
            self,
            skill_id: int,
            name: Optional[str] = None,
            content: Optional[str] = None,
            description: Optional[str] = None,
            category: Optional[str] = None,
        ) -> str:
            async with get_db_session() as db:
                skill = await SkillMapper(db).get_by_id(skill_id)
                if not skill or skill.user_id != user_id:
                    return json.dumps({"error": f"未找到 ID 为 {skill_id} 的技能"}, ensure_ascii=False)
                if skill.scope == SKILL_SCOPE_SYSTEM:
                    return json.dumps({"error": "系统级技能不可修改"}, ensure_ascii=False)
                updated = await SkillService(db).update_skill(
                    skill_id,
                    SkillUpdate(name=name, content=content, description=description, category=category),
                )
                if not updated:
                    return json.dumps({"error": "更新失败"}, ensure_ascii=False)
                return json.dumps({"id": updated.id, "name": updated.name}, ensure_ascii=False)

        def _run(self, **kwargs) -> str:
            raise NotImplementedError("Use async version")

    return [ListMySkillsTool(), GetSkillTool(), UseSkillTool(), CreateSkillTool(), UpdateSkillTool()]
