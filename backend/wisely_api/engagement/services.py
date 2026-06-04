from .models import Event


def log_event(request, event_type, **fields):
    """Append a clickstream Event for a server-performed action.

    ``actor`` and ``session_id`` are taken from the request; ``source_review`` is pulled from
    the request body unless the caller passes it explicitly. Logging never raises — analytics
    must never break the user's action.
    """
    data = getattr(request, "data", {}) or {}
    fields.setdefault(
        "actor", request.user if getattr(request.user, "is_authenticated", False) else None
    )
    fields.setdefault("session_id", data.get("session_id") or "")
    if "source_review" not in fields and "source_review_id" not in fields:
        raw = data.get("source_review")
        if str(raw or "").isdigit():
            fields["source_review_id"] = int(raw)
    try:
        Event.objects.create(event_type=event_type, **fields)
    except Exception:
        pass
