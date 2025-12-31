from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()


import logging
import os

from dash import Dash

from src.config import get_settings
from src.logging_config import configure_logging
from src.supabase_client import make_supabase_client
from src.data.supabase_repo import SupabaseRepo
from src.indicators.registry import build_registry
from src.scheduler.ingest_job import Ingestor, build_owner_id
from src.scheduler.lock import DistributedLock
from src.scheduler.scheduler import build_scheduler
from src.ui.layout import build_layout
from src.ui.callbacks import register_callbacks

settings = get_settings()
configure_logging(settings.log_level)
log = logging.getLogger(__name__)

supabase = make_supabase_client(settings.supabase_url, settings.supabase_key, schema=settings.supabase_schema)
repo = SupabaseRepo(supabase)

# Dash app
app = Dash(__name__, title=settings.app_title, suppress_callback_exceptions=True)
server = app.server  # For gunicorn: gunicorn app:server

app.layout = build_layout(settings)
register_callbacks(settings, repo)

_scheduler_started = False


def _should_start_scheduler() -> bool:
    if not settings.enable_scheduler:
        return False
    # Avoid double-start in dev reloader
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return True
    if os.environ.get("FLASK_ENV") == "development" and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return False
    return True


def start_scheduler_once() -> None:
    global _scheduler_started
    if _scheduler_started:
        return
    if not _should_start_scheduler():
        log.info("Scheduler disabled or not in main process.")
        _scheduler_started = True
        return

    owner_id = build_owner_id(settings)
    lock = DistributedLock(supabase, settings.lock_name, owner_id=owner_id, lease_seconds=settings.lease_seconds)
    ingestor = Ingestor(settings, repo, lock)
    sched = build_scheduler(settings, ingestor)
    sched.start()
    log.info("Background scheduler started (owner_id=%s)", owner_id)
    _scheduler_started = True


start_scheduler_once()

if __name__ == "__main__":
    # Local dev
    app.run_server(host="0.0.0.0", port=int(os.environ.get("PORT", "8050")), debug=True)
