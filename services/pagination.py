"""Pagination for lists that are filtered in Python (e.g. by eligibility rules).

Exposes the same attributes as Flask-SQLAlchemy's Pagination so the shared
`paginate` macro works for both.
"""

import math


class ListPagination:

    def __init__(self, items, total, page, per_page):
        self.total = total
        self.per_page = per_page
        self.pages = max(1, math.ceil(total / per_page))
        self.page = min(max(page, 1), self.pages)
        start = (self.page - 1) * per_page
        self.items = items[start:start + per_page]

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1

    def iter_pages(self, left_edge=1, left_current=2, right_current=2, right_edge=1):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge
                    or (self.page - left_current - 1 < num < self.page + right_current)
                    or num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num
