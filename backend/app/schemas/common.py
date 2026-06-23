"""Shared schema primitives: pagination, sorting, generic responses."""
from __future__ import annotations

from typing import Annotated, Generic, Literal, TypeVar

from pydantic import AfterValidator, BaseModel, Field

T = TypeVar("T")


def _normalize_email(value: str) -> str:
    """Lenient, professional-grade email check.

    Pydantic's ``EmailStr`` rejects reserved/special-use TLDs such as ``.test``
    (so the seeded ``admin@demo.test`` could never log in). We only require an
    ``@`` and a ``.`` in the domain part, then normalize case/whitespace.
    """
    value = value.strip()
    local, sep, domain = value.partition("@")
    if not sep or not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("Enter a valid email address (must contain '@' and '.')")
    return value.lower()


# Drop-in replacement for EmailStr with relaxed validation.
LooseEmail = Annotated[str, AfterValidator(_normalize_email)]


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] = "desc"

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.page_size else 0


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None
