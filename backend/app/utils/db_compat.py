from sqlalchemy import Text
from sqlalchemy.dialects.mysql import LONGTEXT

from app.core.config import settings

IS_SQLITE: bool = settings.DATABASE_URL.startswith("sqlite")

# Maps to LONGTEXT on MySQL, TEXT on SQLite/others
LargeText = Text().with_variant(LONGTEXT(), "mysql")
