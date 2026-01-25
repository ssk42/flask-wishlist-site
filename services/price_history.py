"""Service for managing price history and statistics."""

import logging
import datetime
from sqlalchemy import func
from app import db
from models import PriceHistory

logger = logging.getLogger(__name__)


def record_price_history(
        item_id: int,
        price: float,
        source: str = 'auto') -> bool:
    """
    Record a price point for an item.

    Logic:
    - If no history exists, record.
    - If price changed > $0.01 from last record, record.
    - If price is same but last record > 6 hours old, record for liveness.

    Returns:
        bool: True if a new record was added, False otherwise.
    """
    if price is None or price < 0:
        return False

    try:
        # Get last recorded price
        last_record = PriceHistory.query.filter_by(item_id=item_id)\
            .order_by(PriceHistory.recorded_at.desc())\
            .first()

        should_record = False

        if not last_record:
            should_record = True
        else:
            price_diff = abs(last_record.price - price)
            now = datetime.datetime.now(datetime.timezone.utc)
            last_time = last_record.recorded_at.replace(
                tzinfo=datetime.timezone.utc)
            time_diff = now - last_time

            # Record if price changed significantly (more than 1 cent)
            if price_diff > 0.01:
                should_record = True
            # Or if it's been a while (6 hours) even if price is same
            elif time_diff.total_seconds() > (6 * 3600):
                should_record = True

        if should_record:
            history = PriceHistory(
                item_id=item_id,
                price=price,
                source=source,
                recorded_at=datetime.datetime.now(datetime.timezone.utc)
            )
            db.session.add(history)
            db.session.commit()
            logger.info(
                f"Recorded price history for item {item_id}: "
                f"${price} ({source})")
            return True

        return False

    except Exception as e:
        logger.error(f"Failed to record price history for item {item_id}: {e}")
        db.session.rollback()
        return False


def get_price_history_stats(item_id: int, days: int = 90):
    """
    Get price history statistics (min, max, avg) for an item.
    """
    cutoff = datetime.datetime.now(
        datetime.timezone.utc) - datetime.timedelta(days=days)

    try:
        stats = db.session.query(
            func.min(PriceHistory.price),
            func.max(PriceHistory.price),
            func.avg(PriceHistory.price)
        ).filter(
            PriceHistory.item_id == item_id,
            PriceHistory.recorded_at >= cutoff
        ).first()

        if stats and stats[0] is not None:
            return {
                'min': float(stats[0]),
                'max': float(stats[1]),
                'avg': float(stats[2]),
                'period_days': days
            }
        return None

    except Exception as e:
        logger.error(f"Failed to get history stats for item {item_id}: {e}")
        return None
