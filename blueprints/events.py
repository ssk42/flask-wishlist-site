"""Events blueprint for event management."""

import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from models import db, Event, Item
from services.form_validators import FormValidator
from services.view_helpers import flash_and_redirect

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
        validator = FormValidator(request.form)
        name = validator.required('name', 'Event name is required.')
        event_date = validator.parse_date('date', required=True, error_message='Event date is required.',
                                          format_error='Invalid date format. Please use YYYY-MM-DD.')

        if not validator.is_valid():
            for error in validator.errors:
                flash(error, 'danger')
            return render_template('event_form.html', form_data=request.form.to_dict())

        new_event = Event(
            name=name,
            date=event_date,
            created_by_id=current_user.id
        )
        db.session.add(new_event)
        db.session.commit()
        current_app.logger.info(f'Event created by user_id={current_user.id}: {name}')
        return flash_and_redirect(f'Event "{name}" created successfully!', 'success', 'events.events_list')

    return render_template('event_form.html', form_data={})


@bp.route('/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    """Edit an existing event."""
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)

    if event.created_by_id != current_user.id:
        return flash_and_redirect('You can only edit events you created.', 'danger', 'events.events_list')

    if request.method == 'POST':
        validator = FormValidator(request.form)
        name = validator.required('name', 'Event name is required.')
        event_date = validator.parse_date('date', required=True, error_message='Event date is required.',
                                          format_error='Invalid date format. Please use YYYY-MM-DD.')

        if not validator.is_valid():
            for error in validator.errors:
                flash(error, 'danger')
            return render_template('event_form.html', event=event, form_data=request.form.to_dict())

        event.name = name
        event.date = event_date
        db.session.commit()
        return flash_and_redirect(f'Event "{name}" updated successfully!', 'success', 'events.events_list')

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
        return flash_and_redirect('You can only delete events you created.', 'danger', 'events.events_list')

    # Remove event association from items but don't delete items
    event_name = event.name
    Item.query.filter_by(event_id=event_id).update({'event_id': None})
    db.session.delete(event)
    db.session.commit()
    return flash_and_redirect(f'Event "{event_name}" deleted.', 'info', 'events.events_list')
