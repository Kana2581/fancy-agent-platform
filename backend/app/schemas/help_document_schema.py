from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HelpDocumentSummaryOut(BaseModel):
    id: int
    slug: str
    title: str
    summary: str
    category: Optional[str]
    doc_type: str
    route: Optional[str]
    icon_key: Optional[str]
    sort_order: int

    model_config = {"from_attributes": True}


class HelpDocumentOut(HelpDocumentSummaryOut):
    content: str
    created_at: datetime
    updated_at: datetime
