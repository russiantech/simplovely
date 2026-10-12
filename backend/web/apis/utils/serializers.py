"""Uniform JSON envelopes and pagination helpers."""
from flask import jsonify, request, url_for
from flask_sqlalchemy.pagination import QueryPagination

MAX_PAGE_SIZE = 100


def _text(messages):
    if isinstance(messages, (list, tuple)):
        return " ".join(str(m) for m in messages if m)
    return "" if messages is None else str(messages)


def success_response(message, data=None, status_code=200):
    """``{"success": true, "message": "...", **data}``"""
    body = {"success": True, "message": _text(message)}
    if data:
        body.update(data)
    return jsonify(body), status_code


def error_response(message, status_code=400, data=None):
    """``{"success": false, "error": "..."}`` (status defaults to 400, not 500)."""
    body = {"success": False, "error": _text(message)}
    if data:
        body.update(data)
    return jsonify(body), status_code


def get_pagination(default_size=10, size_keys=("page_size", "per_page", "per_size")):
    """Read ``page`` and page size from the query string, clamped to sane bounds."""
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    size = default_size
    for key in size_keys:
        if request.args.get(key, type=int):
            size = request.args.get(key, type=int)
            break
    return page, min(max(size, 1), MAX_PAGE_SIZE)


def pagination_meta(p):
    return {
        "page": p.page, "per_page": p.per_page, "total": p.total, "total_pages": p.pages,
        "has_next": p.has_next, "has_prev": p.has_prev, "next_num": p.next_num, "prev_num": p.prev_num,
    }


class PageSerializer:
    """Serialise a pagination object or a plain list using each item's ``get_summary``."""

    def __init__(self, pagination_obj=None, items=None, resource_name=None, summary_func=None, context_id=None, **kwargs):
        self.data = {}
        self.resource_name = resource_name or "items"
        self.summary_func = summary_func or (lambda item, **kw: item.get_summary(**kw))
        self.context_id = context_id
        if pagination_obj is not None:
            self._paginated(pagination_obj, **kwargs)
        elif items is not None:
            self._plain(items, **kwargs)
        else:
            raise ValueError("Either `pagination_obj` or `items` must be provided.")

    def _paginated(self, p, **kwargs):
        if not isinstance(p, QueryPagination):
            raise TypeError(f"Expected QueryPagination, got {type(p)}")
        self.items = [self.summary_func(item, **kwargs) for item in p.items]
        args = {"page_size": p.per_page}
        if self.context_id is not None:
            args["context_id"] = self.context_id
        self.data.update(
            total_items_count=p.total,
            offset=(p.page - 1) * p.per_page,
            requested_page_size=p.per_page,
            current_page_number=p.page,
            total_pages_count=p.pages,
            has_next_page=p.has_next,
            has_prev_page=p.has_prev,
            next_page_url=url_for(request.endpoint, page=p.next_num, **args, **request.view_args) if p.has_next else None,
            prev_page_url=url_for(request.endpoint, page=p.prev_num, **args, **request.view_args) if p.has_prev else None,
        )

    def _plain(self, items, **kwargs):
        items = list(items)
        self.items = [self.summary_func(item, **kwargs) for item in items]
        self.data.update(
            total_items_count=len(items), offset=0, requested_page_size=len(items), current_page_number=1,
            total_pages_count=1, has_next_page=False, has_prev_page=False, next_page_url=None, prev_page_url=None,
        )

    def get_data(self):
        return {"success": True, "page_meta": self.data, self.resource_name: self.items}
