from sqlalchemy.sql import ClauseElement


def get_or_create(session, model, defaults=None, **kwargs):
    """Return ``(instance, created)``. Flushes (does not commit) so callers keep one transaction."""
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    params = {k: v for k, v in kwargs.items() if not isinstance(v, ClauseElement)}
    params.update(defaults or {})
    instance = model(**params)
    session.add(instance)
    session.flush()
    return instance, True
