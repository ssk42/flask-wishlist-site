"""Events blueprint for event management."""

import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from models import db, Event, Item

bp = Blueprint('events', __name__, url_prefix='/events')


@bp.route('')
@login_required
def events_list():
    """List all events grouped by upcoming vs past."""
    today = datetime.date.today()

    # Eager load creator and items to prevent N+1 queries
    base_query = Event.query.options(
        joinedload(Event.created_by),
        joinedload(Event.items)
    )

    upcoming_events = base_query.filter(Event.date >= today).order_by(Event.date.asc()).all()
    past_events = base_query.filter(Event.date < today).order_by(Event.date.desc()).all()
    return render_template('events.html', upcoming_events=upcoming_events, past_events=past_events)


@bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_event():
    """Create a new event."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        date_str = request.form.get('date', '').strip()

        if not name:
            flash('Event name is required.', 'danger')
            return render_template('event_form.html', form_data=request.form.to_dict())

        if not date_str:
            flash('Event date is required.', 'danger')
            return render_template('event_form.html', form_data=request.form.to_dict())

        try:
            event_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return render_template('event_form.html', form_data=request.form.to_dict())

        new_event = Event(
            name=name,
            date=event_date,
            created_by_id=current_user.id
        )
        db.session.add(new_event)
        db.session.commit()
        current_app.logger.info(f'Event created by user_id={current_user.id}: {name}')
        flash(f'Event "{name}" created successfully!', 'success')
        return redirect(url_for('events.events_list'))

    return render_template('event_form.html', form_data={})


@bp.route('/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    """Edit an existing event."""
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)

    if event.created_by_id != current_user.id:
        flash('You can only edit events you created.', 'danger')
        return redirect(url_for('events.events_list'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        date_str = request.form.get('date', '').strip()

        if not name:
            flash('Event name is required.', 'danger')
            return render_template('event_form.html', event=event, form_data=request.form.to_dict())

        if not date_str:
            flash('Event date is required.', 'danger')
            return render_template('event_form.html', event=event, form_data=request.form.to_dict())

        try:
            event_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return render_template('event_form.html', event=event, form_data=request.form.to_dict())

        event.name = name
        event.date = event_date
        db.session.commit()
        flash(f'Event "{name}" updated successfully!', 'success')
        return redirect(url_for('events.events_list'))

    form_data = {
        'name': event.name,
        'date': event.date.strftime('%Y-%m-%d')
    }
    return render_template('event_form.html', event=event, form_data=form_data)


@bp.route('/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    """Delete an event."""
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)

    if event.created_by_id != current_user.id:
        flash('You can only delete events you created.', 'danger')
        return redirect(url_for('events.events_list'))

    # Remove event association from items but don't delete items
    Item.query.filter_by(event_id=event_id).update({'event_id': None})
    db.session.delete(event)
    db.session.commit()
    flash(f'Event "{event.name}" deleted.', 'info')
    return redirect(url_for('events.events_list'))
