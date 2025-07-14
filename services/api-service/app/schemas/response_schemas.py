from pydantic import BaseModel, Field
from typing import TypeVar, Generic, Optional, List, Any

# A generic type variable that can be any type.
T = TypeVar('T')

class PaginationMeta(BaseModel):
    """Schema for pagination metadata."""
    total: int = Field(..., description="Total number of all items")
    pageSize: int = Field(..., description="Number of items per page")
    pageNum: int = Field(..., description="The current page number")

class PaginatedData(BaseModel, Generic[T]):
    """Schema for the 'data' field when returning a paginated list."""
    list: List[T]
    meta: PaginationMeta

class StandardResponse(BaseModel, Generic[T]):
    """
    The standard, consistent API response envelope for all successful requests.
    """
    code: int
    message: str
    data: Optional[T] = None 