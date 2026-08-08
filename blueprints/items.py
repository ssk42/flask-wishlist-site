"""Items blueprint for item management, claims, and exports."""

import datetime
import secrets
from collections import OrderedDict, defaultdict
from types import SimpleNamespace
from urllib.parse import urlparse

import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, abort, send_file, current_app, session
)
from flask_login import login_required, current_user
from sqlalchemy import case
from sqlalchemy.orm import joinedload

from models import db, User, Item, Event, Comment, Contribution
from config import PRIORITY_CHOICES, STATUS_CHOICES
from services.utils import get_items_url_with_filters
from services.form_validators import FormValidator, validate_item_fields
from services.session_filter_manager import SessionFilterManager
from services import item_service
from services.item_service import ItemActionError

bp = Blueprint('items', __name__)

DEFAULT_IMAGE_URL = 'https://via.placeholder.com/600x400?text=Wishlist+Item'


def _new_submission_token():
    """Return a token used to make browser form submissions idempotent."""
    return secrets.token_urlsafe(24)


def _completed_submission(token):
    """Return whether this browser has already completed this mutation."""
    return bool(token and token in session.get('item_mutations', {}))


def _remember_submission(token, item_id):
    """Remember successful browser submissions without growing the session forever."""
    if not token:
        return
    mutations = session.get('item_mutations', {})
    mutations[token] = item_id
    # Keep only the most recent completed actions; token ordering is insertion order.
    while len(mutations) > 20:
        mutations.pop(next(iter(mutations)))
    session['item_mutations'] = mutations


def _item_form_data(item, submission_token=None):
    """Return item values in the same shape as a submitted form."""
    data = {
        'description': item.description,
        'link': item.link or '',
        'price': item.price if item.price is not None else '',
        'category': item.category or '',
        'image_url': item.image_url or '',
        'priority': item.priority or '',
        'event_id': item.event_id or '',
        'size': item.size or '',
        'color': item.color or '',
        'quantity': item.quantity if item.quantity is not None else '',
    }
    if submission_token:
        data['submission_token'] = submission_token
    return data


def _get_item_or_404(item_id):
    """Fetch an item by id or abort with 404."""
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)
    return item


def _item_card_response(item, message, category):
    """Render the htmx partial response for claim/unclaim actions.

    Dashboard context gets the compact card plus rendered flash messages;
    the items page gets the full card (flash intentionally omitted there).
    """
    if request.args.get('context') == 'dashboard':
        flash(message, category)
        card_html = render_template('partials/_dashboard_item_card.html', item=item)
        flash_html = render_template('partials/_flash_messages.html')
        return card_html + flash_html
    return render_template('partials/_item_card.html', item=item, default_image_url=DEFAULT_IMAGE_URL)


def _parse_contribution_amount():
    """Parse and validate the split contribution amount from the form.

    Returns (amount, error_response); exactly one is None.
    """
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        flash('Invalid contribution amount.', 'danger')
        return None, redirect(get_items_url_with_filters())
    if amount <= 0:
        flash('Contribution amount must be positive.', 'danger')
        return None, redirect(get_items_url_with_filters())
    return amount, None


@bp.route('/items')
@login_required
def items_list():
    """List all items with filtering, sorting, and grouping."""
    # Use SessionFilterManager for filter persistence
    filter_manager = SessionFilterManager(request)

    if filter_manager.should_clear():
        filter_manager.clear_all()
        return redirect(url_for('items.items_list'))

    filters = filter_manager.get_filters()
    user_filter = filters['user_filter']
    status_filter = filters['status_filter']
    priority_filter = filters['priority_filter']
    event_filter = filters['event_filter']
    search_query = filters['q']
    sort_by = filters['sort_by']
    sort_order = filters['sort_order']

    query = (
        Item.query.options(
            joinedload(Item.user),
            joinedload(Item.last_updated_by),
            joinedload(Item.comments).joinedload(Comment.author),
            joinedload(Item.contributions).joinedload(Contribution.user)
        )
        .join(User, Item.user_id == User.id)
    )

    if user_filter:
        query = query.filter(Item.user_id == user_filter)

    if status_filter:
        query = query.filter(Item.status == status_filter)

    if priority_filter:
        query = query.filter(Item.priority == priority_filter)

    if event_filter:
        query = query.filter(Item.event_id == event_filter)

    if search_query:
        ilike_query = f"%{search_query}%"
        query = query.filter(Item.description.ilike(ilike_query))

    priority_order = case(
        (Item.priority == 'High', 1),
        (Item.priority == 'Medium', 2),
        (Item.priority == 'Low', 3),
        else_=4
    )

    sort_columns = {
        'price': Item.price,
        'status': Item.status,
        'description': Item.description,
        'category': Item.category,
        'created': Item.id,
        'user': User.name
    }

    if sort_by == 'priority':
        order_criteria = priority_order.asc() if sort_order == 'asc' else priority_order.desc()
    else:
        column = sort_columns.get(sort_by, Item.price)
        order_criteria = column.asc() if sort_order == 'asc' else column.desc()

    query = query.order_by(order_criteria, Item.description.asc())

    all_items = query.all()

    totals_dict = defaultdict(lambda: {'count': 0, 'total': 0.0})
    grouped_items = OrderedDict()
    for item in all_items:
        # For summary totals, exclude the current user's own claimed/purchased items to preserve surprise
        if item.user_id == current_user.id and item.status in ['Claimed', 'Purchased']:
            # Skip adding to totals_dict for surprise protection
            pass
        else:
            key = (item.user_id, item.status)
            totals_dict[key]['count'] += 1
            if item.price:
                totals_dict[key]['total'] += float(item.price)

        group = grouped_items.setdefault(item.user_id, SimpleNamespace(user=item.user, items=[]))
        group.items.append(item)

    users = User.query.order_by(User.name).all()

    user_lookup = {user.id: user for user in users}
    summary_rows = []
    for (user_id, status), data in totals_dict.items():
        summary_rows.append({
            'user': user_lookup.get(user_id),
            'status': status,
            'count': data['count'],
            'total': data['total']
        })

    summary_rows.sort(key=lambda row: ((row['user'].name if row['user'] else ''), row['status']))

    event_options = Event.query.order_by(Event.date.desc()).all()
    status_options = [value for value, in db.session.query(Item.status).filter(Item.status.isnot(None)).distinct().order_by(Item.status)]
    status_options = sorted(set(status_options + STATUS_CHOICES))

    active_filters = {
        'user_filter': user_filter,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'event_filter': event_filter,
        'q': search_query,
        'sort_by': sort_by,
        'sort_order': sort_order
    }

    sort_options = [
        ('priority', 'Priority'),
        ('price', 'Price'),
        ('status', 'Status'),
        ('description', 'Description'),
        ('category', 'Category'),
        ('user', 'User'),
        ('created', 'Recently Added')
    ]

    return render_template(
        'items_list.html',
        grouped_items=list(grouped_items.values()),
        users=users,
        summary_rows=summary_rows,
        status_options=status_options,
        priority_choices=PRIORITY_CHOICES,
        event_options=event_options,
        active_filters=active_filters,
        sort_options=sort_options,
        default_image_url=DEFAULT_IMAGE_URL
    )


@bp.route('/submit_item', methods=['GET', 'POST'])
@login_required
def submit_item():
    """Create a new wishlist item."""
    # Get upcoming events for the dropdown
    today = datetime.date.today()
    upcoming_events = Event.query.filter(Event.date >= today).order_by(Event.date.asc()).all()

    if request.method == 'POST':
        form_data = request.form.to_dict()
        submission_token = form_data.get('submission_token')
        if _completed_submission(submission_token):
            flash('This item was already added.', 'info')
            return redirect(get_items_url_with_filters())
        validator = FormValidator(form_data)

        description = validator.required('description', 'A description is required to create an item.')
        link = validator.optional('link')
        image_url = validator.optional('image_url')
        category = validator.optional('category')
        priority = validator.choice('priority', PRIORITY_CHOICES, default=PRIORITY_CHOICES[0])
        status = validator.choice('status', STATUS_CHOICES, default=STATUS_CHOICES[0])
        event_id = validator.parse_int('event_id')
        price = validator.parse_float('price', 'Price must be a valid number.')
        size = validator.optional('size', max_length=50)
        color = validator.optional('color', max_length=50)
        quantity = validator.parse_int('quantity', 'Quantity must be a valid number.',
                                       min_value=1, max_value=99, range_error='Quantity must be between 1 and 99.')
        validate_item_fields(validator, description, link, image_url, price, event_id)

        if not validator.is_valid():
            for error in validator.errors:
                flash(error, 'danger')
            form_data['submission_token'] = submission_token or _new_submission_token()
            return render_template('submit_item.html', status_choices=STATUS_CHOICES,
                                   priority_choices=PRIORITY_CHOICES, events=upcoming_events, form_data=form_data)

        new_item = Item(
            description=description,
            link=link,
            price=price,
            category=category,
            image_url=image_url,
            priority=priority,
            status=status,
            user_id=current_user.id,
            event_id=event_id,
            size=size,
            color=color,
            quantity=quantity
        )

        try:
            db.session.add(new_item)
            db.session.commit()
            _remember_submission(submission_token, new_item.id)
            current_app.logger.info(f'Item created by user_id={current_user.id}: {description[:50]}')
            flash('Item added to your wishlist!', 'success')
            return redirect(get_items_url_with_filters())
        except Exception as exc:
            current_app.logger.error(f'Failed to create item for user_id={current_user.id}: {str(exc)}', exc_info=True)
            db.session.rollback()
            flash('Failed to create item. Please try again.', 'danger')
            form_data['submission_token'] = submission_token or _new_submission_token()
            return render_template('submit_item.html', status_choices=STATUS_CHOICES,
                                   priority_choices=PRIORITY_CHOICES, events=upcoming_events, form_data=form_data)

    return render_template('submit_item.html', status_choices=STATUS_CHOICES,
                           priority_choices=PRIORITY_CHOICES, events=upcoming_events,
                           form_data={'submission_token': _new_submission_token()})


@bp.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Edit an existing item."""
    item = _get_item_or_404(item_id)

    # Get upcoming events for the dropdown (only for item owner)
    today = datetime.date.today()
    upcoming_events = Event.query.filter(Event.date >= today).order_by(Event.date.asc()).all()

    if request.method == 'POST':
        form_data = request.form.to_dict()
        submission_token = form_data.get('submission_token')

        if _completed_submission(submission_token):
            flash('Those changes were already saved.', 'info')
            return redirect(get_items_url_with_filters())

        if item.user_id != current_user.id:
            # Non-owner can only update status
            status = form_data.get('status')
            if status not in STATUS_CHOICES:
                flash('Please choose a valid status.', 'danger')
            else:
                item.status = status
                item.last_updated_by_id = current_user.id
                try:
                    db.session.commit()
                    _remember_submission(submission_token, item.id)
                    flash('Status updated successfully.', 'success')
                    return redirect(get_items_url_with_filters())
                except Exception as exc:
                    current_app.logger.error(f'Failed to update status for item_id={item.id}: {exc}', exc_info=True)
                    db.session.rollback()
                    flash('Failed to update status. Please try again.', 'danger')
                    return render_template('edit_item.html', item=item, current_user=current_user,
                                           status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES,
                                           events=upcoming_events, form_data=form_data)
        else:
            # Owner can edit all fields
            validator = FormValidator(form_data)
            description = validator.required('description', 'Description cannot be empty.')
            link = validator.optional('link')
            price = validator.parse_float('price', 'Price must be a valid number.')
            image_url = validator.optional('image_url')
            quantity = validator.parse_int('quantity', 'Quantity must be a valid number.',
                                           min_value=1, max_value=99, range_error='Quantity must be between 1 and 99.')
            event_id = validator.parse_int('event_id')
            priority = validator.choice('priority', PRIORITY_CHOICES, error_message='Please choose a valid priority.')
            validate_item_fields(validator, description, link, image_url, price, event_id)

            if not validator.is_valid():
                for error in validator.errors:
                    flash(error, 'danger')
                return render_template('edit_item.html', item=item, current_user=current_user,
                                       status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES,
                                       events=upcoming_events, form_data=form_data)

            item.description = description
            item.link = link
            item.price = price
            item.category = validator.optional('category')
            item.image_url = image_url
            if priority:
                item.priority = priority
            item.event_id = event_id
            item.size = validator.optional('size', max_length=50)
            item.color = validator.optional('color', max_length=50)
            item.quantity = quantity

            try:
                db.session.commit()
                _remember_submission(submission_token, item.id)
                flash('Item updated successfully.', 'success')
                return redirect(get_items_url_with_filters())
            except Exception as exc:
                current_app.logger.error(f'Failed to update item_id={item.id}: {exc}', exc_info=True)
                db.session.rollback()
                flash('Failed to update item. Please try again.', 'danger')
                return render_template('edit_item.html', item=item, current_user=current_user,
                                       status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES,
                                       events=upcoming_events, form_data=form_data)

    return render_template('edit_item.html', item=item, current_user=current_user,
                           status_choices=STATUS_CHOICES, priority_choices=PRIORITY_CHOICES,
                           events=upcoming_events,
                           form_data=_item_form_data(item, _new_submission_token()))


@bp.route('/claim_item/<int:item_id>', methods=['POST'])
@login_required
def claim_item(item_id):
    """Claim an item for purchase."""
    item = _get_item_or_404(item_id)

    try:
        item_service.claim_item(item, current_user.id)
    except ItemActionError as err:
        flash(err.message, 'warning')
        return redirect(get_items_url_with_filters())

    # For htmx requests, return the updated item card
    if request.headers.get('HX-Request'):
        return _item_card_response(item, f'You have claimed "{item.description}".', 'success')

    flash(f'You have claimed "{item.description}".', 'success')
    return redirect(get_items_url_with_filters())


@bp.route('/unclaim_item/<int:item_id>', methods=['POST'])
@login_required
def unclaim_item(item_id):
    """Unclaim an item back to Available status."""
    item = _get_item_or_404(item_id)

    try:
        item_service.unclaim_item(item, current_user.id)
    except ItemActionError:
        flash('You cannot unclaim this item.', 'danger')
        return redirect(get_items_url_with_filters())

    if request.headers.get('HX-Request'):
        return _item_card_response(item, f'You have unclaimed "{item.description}".', 'info')

    flash(f'You have unclaimed "{item.description}".', 'info')
    return redirect(get_items_url_with_filters())


@bp.route('/items/<int:item_id>/modal')
@login_required
def get_item_modal(item_id):
    """Get item quick-view modal content."""
    item = db.session.get(Item, item_id)
    if item is None:
        return 'Item not found', 404
    return render_template('partials/_item_quick_view.html', item=item)


@bp.route('/items/<int:item_id>/split-modal')
@login_required
def get_split_modal(item_id):
    """Get split gift modal content for dynamic loading."""
    item = _get_item_or_404(item_id)

    return render_template('partials/_split_modal.html', item=item, default_image_url=DEFAULT_IMAGE_URL)


@bp.route('/item/<int:item_id>/refresh-price', methods=['POST'])
@login_required
def refresh_price(item_id):
    """Refresh the price for an item by fetching from its URL."""
    from services.price_service import refresh_item_price

    item = _get_item_or_404(item_id)

    if not item.link:
        flash('This item has no link to fetch price from.', 'warning')
        return redirect(get_items_url_with_filters())

    success, new_price, message = refresh_item_price(item, db)

    if success:
        flash(f'Price updated: {message}', 'success')
    else:
        # Give more helpful error message for Amazon
        domain = urlparse(item.link).netloc.lower()
        if 'amazon' in domain:
            flash('Amazon blocks automated price fetching. You can update the price manually by editing the item.', 'warning')
        else:
            flash('Could not fetch price automatically. You can update it manually by editing the item.', 'warning')

    return redirect(get_items_url_with_filters())


@bp.route('/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    """Delete an item (owner only)."""
    item = db.session.get(Item, item_id)
    if item is None:
        flash('Item not found or already deleted.', 'warning')
        return redirect(get_items_url_with_filters())
    if item.user_id != current_user.id:
        flash('You do not have permission to delete this item.', 'danger')
        return redirect(get_items_url_with_filters())

    try:
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted.', 'info')
    except Exception as exc:
        current_app.logger.error(f'Failed to delete item_id={item_id}: {exc}', exc_info=True)
        db.session.rollback()
        flash('Failed to delete item. Please try again.', 'danger')
    return redirect(get_items_url_with_filters())


@bp.route('/my-claims')
@login_required
def my_claims():
    """Show items the current user has claimed or purchased for others."""
    items = (
        Item.query.options(
            joinedload(Item.user),
            joinedload(Item.last_updated_by),
            joinedload(Item.comments).joinedload(Comment.author)
        )
        .filter(
            Item.last_updated_by_id == current_user.id,
            Item.status.in_(['Claimed', 'Purchased']),
            Item.user_id != current_user.id  # Exclude own items
        )
        .order_by(Item.user_id, Item.description)
        .all()
    )

    # Fetch split contributions
    contributions = (
        Contribution.query
        .options(
            joinedload(Contribution.item).joinedload(Item.user),
            joinedload(Contribution.item).joinedload(Item.contributions)
        )
        .filter_by(user_id=current_user.id)
        .order_by(Contribution.created_at.desc())
        .all()
    )

    # Group items by recipient (item owner)
    grouped_items = OrderedDict()
    for item in items:
        group = grouped_items.setdefault(item.user_id, SimpleNamespace(user=item.user, items=[]))
        group.items.append(item)

    # Count of claimed (not yet purchased) items for the badge
    claimed_count = sum(1 for item in items if item.status == 'Claimed')
    purchased_count = sum(1 for item in items if item.status == 'Purchased')

    return render_template(
        'my_claims.html',
        grouped_items=list(grouped_items.values()),
        claimed_count=claimed_count,
        purchased_count=purchased_count,
        status_choices=STATUS_CHOICES,
        default_image_url=DEFAULT_IMAGE_URL,
        contributions=contributions
    )


@bp.route('/export_my_status_updates')
@login_required
def export_my_status_updates():
    """Export current user's claimed/purchased items to Excel."""
    items = Item.query.filter_by(last_updated_by_id=current_user.id).all()

    data = {
        'Description': [item.description for item in items],
        'Status': [item.status for item in items],
        'Price': [item.price for item in items],
        'Updated By': [item.last_updated_by.name for item in items]
    }
    df = pd.DataFrame(data)

    filename = f'status_updates_by_{current_user.name}.xlsx'
    df.to_excel(filename, index=False)

    return send_file(filename, as_attachment=True)


@bp.route('/items/<int:item_id>/split', methods=['POST'])
@login_required
def start_split(item_id):
    """Start a split on an available item."""
    item = _get_item_or_404(item_id)

    if item.user_id == current_user.id:
        flash('You cannot split your own item.', 'warning')
        return redirect(get_items_url_with_filters())

    if item.status != 'Available':
        flash('Item is not available for splitting.', 'warning')
        return redirect(get_items_url_with_filters())

    # Get amount from form
    amount, error = _parse_contribution_amount()
    if error:
        return error

    # Create contribution
    contribution = Contribution(
        item_id=item.id,
        user_id=current_user.id,
        amount=amount,
        is_organizer=True
    )
    
    item.status = 'Splitting'
    db.session.add(contribution)
    db.session.commit()

    flash(f'You started a split for "{item.description}".', 'success')
    return redirect(get_items_url_with_filters())


@bp.route('/items/<int:item_id>/contribute', methods=['POST'])
@login_required
def join_split(item_id):
    """Join an existing split."""
    item = _get_item_or_404(item_id)

    if item.status != 'Splitting':
        flash('Item is not currently being split.', 'warning')
        return redirect(get_items_url_with_filters())

    # Check if already contributing
    existing = Contribution.query.filter_by(item_id=item.id, user_id=current_user.id).first()
    if existing:
        flash('You are already contributing to this split.', 'warning')
        return redirect(get_items_url_with_filters())

    amount, error = _parse_contribution_amount()
    if error:
        return error

    contribution = Contribution(
        item_id=item.id,
        user_id=current_user.id,
        amount=amount,
        is_organizer=False
    )
    
    db.session.add(contribution)
    db.session.commit()

    flash(f'You contributed ${amount:.2f} to "{item.description}".', 'success')
    return redirect(get_items_url_with_filters())


@bp.route('/items/<int:item_id>/withdraw', methods=['POST'])
@login_required
def withdraw_contribution(item_id):
    """Withdraw contribution from a split."""
    item = _get_item_or_404(item_id)

    contribution = Contribution.query.filter_by(item_id=item.id, user_id=current_user.id).first()
    if not contribution:
        flash('You are not contributing to this item.', 'warning')
        return redirect(get_items_url_with_filters())

    is_organizer = contribution.is_organizer
    db.session.delete(contribution)
    
    # If this was the last contribution, reset item to Available
    remaining_contributions = Contribution.query.filter(
        Contribution.item_id == item.id, 
        Contribution.id != contribution.id
    ).order_by(Contribution.created_at).all()

    if not remaining_contributions:
        item.status = 'Available'
    elif is_organizer:
        # Reassign organizer role to the next oldest contributor
        remaining_contributions[0].is_organizer = True

    db.session.commit()
    flash('Contribution withdrawn.', 'info')
    return redirect(get_items_url_with_filters())


@bp.route('/items/<int:item_id>/complete-split', methods=['POST'])
@login_required
def complete_split(item_id):
    """Mark split gift as purchased (Organizer only)."""
    item = _get_item_or_404(item_id)

    contribution = Contribution.query.filter_by(item_id=item.id, user_id=current_user.id).first()

    if not contribution or not contribution.is_organizer:
        flash('Only the split organizer can mark this as purchased.', 'danger')
        return redirect(get_items_url_with_filters())

    item.status = 'Purchased'
    item.last_updated_by_id = current_user.id  # Organizer gets the credit in last_updated_by
    db.session.commit()

    flash(f'"{item.description}" marked as purchased! All contributors will be notified.', 'success')
    # TODO: Send notifications to other contributors
    
    return redirect(get_items_url_with_filters())
