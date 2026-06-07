from app.mappers.base_mapper import BaseMapper
from app.models.image_tool import ImageTool


class ImageToolMapper(BaseMapper[ImageTool]):
    model = ImageTool
