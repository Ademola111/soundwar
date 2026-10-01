from datetime import datetime, timedelta
import os
import threading
import time
from soundwarapp import db
from soundwarapp.models import Artist
from soundwarapp.utils.email import send_reparticipation_email


def process_reparticipation_notifications(current_app):
    """Send emails to past winners who are now eligible to re-enter."""
    target_app = current_app

    with target_app.app_context():
        notification_count = 0
        artists = Artist.query.filter(Artist.wins.any()).all()

        for artist in artists:
            try:
                if artist.needs_reparticipation_notification():
                    if not artist.user or not artist.user.email:
                        continue

                    success = send_reparticipation_email(
                        artist.user.email,
                        artist.user.username,
                        artist.stage_name,
                    )

                    if success:
                        artist.reparticipation_notified_at = datetime.utcnow()
                        notification_count += 1
            except Exception as exc:
                target_app.logger.error(
                    f"Failed to send re-participation notification for artist {artist.id}: {exc}"
                )

        if notification_count > 0:
            db.session.commit()

        return notification_count


def _reparticipation_scheduler(current_app):
    with current_app.app_context():
        interval_hours = int(current_app.config.get("REPARTICIPATION_REMINDER_INTERVAL_HOURS", 24))
        interval_seconds = max(interval_hours, 1) * 3600

        while True:
            try:
                current_app.logger.info("Running past-winner re-participation notification sweep...")
                notifications_sent = process_reparticipation_notifications(current_app)
                current_app.logger.info(f"Re-participation notifications sent: {notifications_sent}")
            except Exception as exc:
                current_app.logger.error(f"Re-participation scheduler error: {exc}")
            time.sleep(interval_seconds)


def start_reparticipation_scheduler(current_app):
    if current_app.config.get("TESTING"):
        return

    if current_app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    thread = threading.Thread(target=_reparticipation_scheduler, args=(current_app,), daemon=True)
    thread.start()
