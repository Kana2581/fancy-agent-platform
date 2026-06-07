import re
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class ImageReference:
    ref_id: str
    object_key: str
    label: str
    source: str


_image_references: ContextVar[List[ImageReference]] = ContextVar(
    "image_references",
    default=[],
)


def set_image_references(references: List[ImageReference]) -> None:
    _image_references.set(list(references))


def get_image_references() -> List[ImageReference]:
    return list(_image_references.get())


def resolve_image_ref_id(source_image_id: Any) -> Optional[ImageReference]:
    normalized = _normalize_ref_id(source_image_id)
    if not normalized:
        return None

    for reference in _image_references.get():
        if reference.ref_id == normalized:
            return reference
    return None


def _normalize_ref_id(value: Any) -> Optional[str]:
    value = str(value).strip().lower()
    if not value:
        return None

    match = re.search(r"(?:image[_\s#-]*)?(\d+)", value)
    if not match:
        return None
    return match.group(1)
