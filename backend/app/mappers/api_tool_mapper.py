from app.mappers.base_mapper import BaseMapper
from app.models.api_tool import ApiTool


class ApiToolMapper(BaseMapper[ApiTool]):
    model = ApiTool
