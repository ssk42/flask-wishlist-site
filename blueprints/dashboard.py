"""Dashboard blueprint for home page and general exports."""

import datetime
import pandas as pd
from flask import Blueprint, render_template, send_file
from flask_login import current_user
from sqlalchemy.orm import joinedload

from models import db, User, Item, Event

bp = Blueprint('dashboard', __name__)


@bp.route('/')
def index():
    """Render the dashboard/home page."""
    dashboard_data = None
    recent_items = []
    upcoming_events = []
    today = datetime.date.today()

    if current_user.is_authenticated:
        claimed_count = Item.query.filter(
            Item.last_updated_by_id == current_user.id,
            Item.status == 'Claimed',
            Item.user_id != current_user.id
        ).count()
        purchased_count = Item.query.filter(
            Item.last_updated_by_id == current_user.id,
            Item.status == 'Purchased',
            Item.user_id != current_user.id
        ).count()
        dashboard_data = {
            'claimed_count': claimed_count,
            'purchased_count': purchased_count
        }

        # Fetch recent items from other users
        recent_items = Item.query.options(joinedload(Item.user))\
            .filter(Item.user_id != current_user.id)\
            .order_by(Item.id.desc())\
            .limit(6).all()

        # Fetch upcoming events
        upcoming_events = Event.query.filter(Event.date >= today)\
            .order_by(Event.date.asc())\
            .limit(3).all()

    return render_template('index.html',
                           dashboard_data=dashboard_data,
                           recent_items=recent_items,
                           upcoming_events=upcoming_events,
                           today=today)


@bp.route('/export_items')
def export_items():
    """Export all items to Excel file."""
    items = Item.query.all()

    # Create a DataFrame
    data = {
        'User': [item.user.name for item in items],
        'Description': [item.description for item in items],
        'Link': [item.link for item in items],
        'Comment': [item.comment for item in items],
        'Price': [item.price for item in items],
        'Year': [item.year for item in items]
    }
    df = pd.DataFrame(data)

    # Convert DataFrame to Excel
    filename = 'allWishlistItems.xlsx'
    df.to_excel(filename, index=False)

    return send_file(filename, as_attachment=True)
