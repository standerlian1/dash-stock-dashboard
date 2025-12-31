from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import Settings
from .ingest_job import Ingestor

log = logging.getLogger(__name__)

NY_TZ = ZoneInfo("America/New_York")


def build_scheduler(settings: Settings, ingestor: Ingestor) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=NY_TZ)

    # Intraday job: run at :00 and :30 during NY session hours.
    # We additionally guard inside the job to ensure starting at 09:30 and ending 16:00.
    intraday_trigger = CronTrigger(day_of_week="mon-fri", hour="9-16", minute="0,30", timezone=NY_TZ)
    scheduler.add_job(
        ingestor.ingest_intraday_if_market_open,
        intraday_trigger,
        id="intraday_ingestion",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    # Daily job: run after close (16:20 NY)
    daily_trigger = CronTrigger(day_of_week="mon-fri", hour="16", minute="20", timezone=NY_TZ)
    scheduler.add_job(
        ingestor.ingest_daily_after_close,
        daily_trigger,
        id="daily_ingestion",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )

    return scheduler
