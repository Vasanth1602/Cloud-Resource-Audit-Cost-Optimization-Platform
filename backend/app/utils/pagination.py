from __future__ import annotations

import math
from typing import Any


class Paginator:
    def __init__(self, page: int = 1, limit: int = 20) -> None:
        self.page = max(1, page)
        self.limit = min(max(1, limit), 100)
        self.offset = (self.page - 1) * self.limit

    def paginate_result(self, total: int, items: list[Any]) -> dict[str, Any]:
        pages = math.ceil(total / self.limit) if total > 0 else 1
        return {
            "total": total,
            "page": self.page,
            "limit": self.limit,
            "pages": pages,
            "items": items,
        }
