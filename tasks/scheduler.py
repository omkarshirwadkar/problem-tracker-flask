from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from main import create_app
from problems.sync import incremental_sync_from_current_size

app = create_app()
scheduler = BlockingScheduler(timezone=ZoneInfo("Asia/Kolkata"))

@scheduler.scheduled_job(CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=ZoneInfo("Asia/Kolkata")))
def weekly_sync():
    with app.app_context():
        incremental_sync_from_current_size()

if __name__ == "__main__":
    scheduler.start()
