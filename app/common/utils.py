from datetime import datetime, UTC


def get_utc_now() -> datetime:
    return datetime.now(UTC)
