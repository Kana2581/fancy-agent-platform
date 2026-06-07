from fastapi import APIRouter, Depends, Query

from app.deps.service import get_stats_service
from app.deps.user import get_current_user
from app.schemas.stats_schema import TokenSummary, AgentTokenStatList, DailyTokenStatList
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/tokens/summary", response_model=TokenSummary)
async def get_token_summary(
    user_id: int = Depends(get_current_user),
    service: StatsService = Depends(get_stats_service),
):
    return await service.get_summary(user_id)


@router.get("/tokens/by-agent", response_model=AgentTokenStatList)
async def get_tokens_by_agent(
    user_id: int = Depends(get_current_user),
    service: StatsService = Depends(get_stats_service),
):
    items = await service.get_by_agent(user_id)
    return AgentTokenStatList(items=items)


@router.get("/tokens/daily", response_model=DailyTokenStatList)
async def get_daily_tokens(
    days: int = Query(default=30, ge=1, le=90),
    user_id: int = Depends(get_current_user),
    service: StatsService = Depends(get_stats_service),
):
    items = await service.get_daily(user_id, days)
    return DailyTokenStatList(items=items)
