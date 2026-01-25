"""Items blueprint for item management, claims, and exports."""

import datetime
from collections import OrderedDict, defaultdict
from types import SimpleNamespace
from urllib.parse import urlparse

import pandas as pd
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, abort, session, send_file, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import case
from sqlalchemy.orm import joinedload

from models import db, User, Item, Event, Comment, Contribution
from config import PRIORITY_CHOICES, STATUS_CHOICES
from services.utils import get_items_url_with_filters

bp = Blueprint('items', __name__)


@bp.route('/items')
@login_required
def items_list():
    """List all items with filtering, sorting, and grouping."""
    # Check if we should clear filters (when explicitly requested)
    clear_filters = request.args.get('clear_filters') == 'true'

    if clear_filters:
        # Clear all filters from session
        session.pop('user_filter', None)
        session.pop('status_filter', None)
        session.pop('priority_filter', None)
        session.pop('event_filter', None)
        session.pop('q', None)
        session.pop('sort_by', None)
        session.pop('sort_order', None)
        return redirect(url_for('items.items_list'))

    # Get filters from request args (for new filter applications)
    user_filter = request.args.get('user_filter', type=int)
    status_filter = request.args.get('status_filter')
    priority_filter = request.args.get('priority_filter')
    event_filter = request.args.get('event_filter', type=int)
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort_by', 'priority')
    sort_order = request.args.get('sort_order', 'asc')

    # If filters are provided in the request, save them to session
    if any(
        [user_filter, status_filter, priority_filter, event_filter,
         search_query]) or request.args.get('sort_by') or request.args.get(
            'sort_order'):
        session['user_filter'] = user_filter
        session['status_filter'] = status_filter
        session['priority_filter'] = priority_filter
        session['event_filter'] = event_filter
        session['q'] = search_query
        session['sort_by'] = sort_by
        session['sort_order'] = sort_order
    else:
        # Use filters from session if no new filters provided
        user_filter = session.get('user_filter')
        status_filter = session.get('status_filter')
        priority_filter = session.get('priority_filter')
        event_filter = session.get('event_filter')
        search_query = session.get('q', '')
        sort_by = session.get('sort_by', 'priority')
        sort_order = session.get('sort_order', 'asc')

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
        if sort_order == 'asc':
            order_criteria = priority_order.asc()
        else:
            order_criteria = priority_order.desc()
    else:
        column = sort_columns.get(sort_by, Item.price)
        order_criteria = column.asc() if sort_order == 'asc' else column.desc()

    query = query.order_by(order_criteria, Item.description.asc())

    all_items = query.all()

    totals_dict = defaultdict(lambda: {'count': 0, 'total': 0.0})
    grouped_items = OrderedDict()
    for item in all_items:
        # For summary totals, exclude the current user's own claimed/purchased
        # items to preserve surprise
        if item.user_id == current_user.id and item.status in [
                'Claimed', 'Purchased']:
            # Skip adding to totals_dict for surprise protection
            pass
        else:
            key = (item.user_id, item.status)
            totals_dict[key]['count'] += 1
            if item.price:
                totals_dict[key]['total'] += float(item.price)

        group = grouped_items.setdefault(
            item.user_id, SimpleNamespace(
                user=item.user, items=[]))
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

    summary_rows.sort(
        key=lambda row: (
            (row['user'].name if row['user'] else ''),
            row['status']))

    event_options = Event.query.order_by(Event.date.desc()).all()
    status_options = [
        value for value,
        in db.session.query(
            Item.status).filter(
            Item.status.isnot(None)).distinct().order_by(
                Item.status)]
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

    default_image_url = (
        'https://via.placeholder.com/600x400?text=Wishlist+Item'
    )

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
        default_image_url=default_image_url
    )


@bp.route('/submit_item', methods=['GET', 'POST'])
@login_required
def submit_item():
    """Create a new wishlist item."""
    # Get upcoming events for the dropdown
    today = datetime.date.today()
    upcoming_events = Event.query.filter(
        Event.date >= today).order_by(
        Event.date.asc()).all()

    if request.method == 'POST':
        form_data = request.form.to_dict()
        description = form_data.get('description', '').strip()
        if not description:
            flash('A description is required to create an item.', 'danger')
            return render_template(
                'submit_item.html',
                status_choices=STATUS_CHOICES,
                priority_choices=PRIORITY_CHOICES,
                events=upcoming_events,
                form_data=form_data)

        link = form_data.get('link', '').strip() or None
        image_url = form_data.get('image_url', '').strip() or None
        category = form_data.get('category', '').strip() or None
        priority = form_data.get('priority') if form_data.get(
            'priority') in PRIORITY_CHOICES else PRIORITY_CHOICES[0]
        status = form_data.get('status') if form_data.get(
            'status') in STATUS_CHOICES else STATUS_CHOICES[0]

        # Handle event_id
        event_id_str = form_data.get('event_id', '').strip()
        event_id = int(event_id_str) if event_id_str else None

        price_input = form_data.get('price', '').strip()
        try:
            price = float(price_input) if price_input else None
        except ValueError:
            flash('Price must be a valid number.', 'danger')
            return render_template(
                'submit_item.html',
                status_choices=STATUS_CHOICES,
                priority_choices=PRIORITY_CHOICES,
                events=upcoming_events,
                form_data=form_data)

        # Handle variant fields (size, color, quantity)
        size = form_data.get('size', '').strip()[:50] or None
        color = form_data.get('color', '').strip()[:50] or None
        quantity_input = form_data.get('quantity', '').strip()
        quantity = None
        if quantity_input:
            try:
                quantity = int(quantity_input)
                if quantity < 1 or quantity > 99:
                    flash('Quantity must be between 1 and 99.', 'danger')
                    return render_template(
                        'submit_item.html',
                        status_choices=STATUS_CHOICES,
                        priority_choices=PRIORITY_CHOICES,
                        events=upcoming_events,
                        form_data=form_data)
            except ValueError:
                flash('Quantity must be a valid number.', 'danger')
                return render_template(
                    'submit_item.html',
                    status_choices=STATUS_CHOICES,
                    priority_choices=PRIORITY_CHOICES,
                    events=upcoming_events,
                    form_data=form_data)

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
            current_app.logger.info(
                f'Item created by user_id={current_user.id}: '
                f'{description[:50]}')
            flash('Item added to your wishlist!', 'success')
            return redirect(get_items_url_with_filters())
        except Exception as exc:
            current_app.logger.error(
                f'Failed to create item for user_id={current_user.id}: '
                f'{str(exc)}', exc_info=True)
            db.session.rollback()
            flash('Failed to create item. Please try again.', 'danger')
            return render_template(
                'submit_item.html',
                status_choices=STATUS_CHOICES,
                priority_choices=PRIORITY_CHOICES,
                events=upcoming_events,
                form_data=form_data)

    return render_template(
        'submit_item.html',
        status_choices=STATUS_CHOICES,
        priority_choices=PRIORITY_CHOICES,
        events=upcoming_events,
        form_data={})


@bp.route('/edit_item/<int:item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Edit an existing item."""
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)

    # Get upcoming events for the dropdown (only for item owner)
    today = datetime.date.today()
    upcoming_events = Event.query.filter(
        Event.date >= today).order_by(
        Event.date.asc()).all()

    if request.method == 'POST':
        form_data = request.form.to_dict()

        if item.user_id != current_user.id:
            # Non-owner can only update status
            status = form_data.get('status')
            if status not in STATUS_CHOICES:
                flash('Please choose a valid status.', 'danger')
            else:
                item.status = status
                item.last_updated_by_id = current_user.id
                db.session.commit()
                flash('Status updated successfully.', 'success')
                return redirect(get_items_url_with_filters())
        else:
            # Owner can edit all fields
            description = form_data.get('description', '').strip()
            if not description:
                flash('Description cannot be empty.', 'danger')
                return render_template(
                    'edit_item.html',
                    item=item,
                    current_user=current_user,
                    status_choices=STATUS_CHOICES,
                    priority_choices=PRIORITY_CHOICES,
                    events=upcoming_events)

            price_input = form_data.get('price', '').strip()
            try:
                price = float(price_input) if price_input else None
            except ValueError:
                flash('Price must be a valid number.', 'danger')
                return render_template(
                    'edit_item.html',
                    item=item,
                    current_user=current_user,
                    status_choices=STATUS_CHOICES,
                    priority_choices=PRIORITY_CHOICES,
                    events=upcoming_events)

            item.description = description
            item.link = form_data.get('link', '').strip() or None
            item.price = price
            item.category = form_data.get('category', '').strip() or None
            item.image_url = form_data.get('image_url', '').strip() or None
            priority = form_data.get('priority')
            if priority in PRIORITY_CHOICES:
                item.priority = priority

            # Handle event_id
            event_id_str = form_data.get('event_id', '').strip()
            item.event_id = int(event_id_str) if event_id_str else None

            # Handle variant fields (size, color, quantity)
            item.size = form_data.get('size', '').strip()[:50] or None
            item.color = form_data.get('color', '').strip()[:50] or None
            quantity_input = form_data.get('quantity', '').strip()
            if quantity_input:
                try:
                    quantity = int(quantity_input)
                    if quantity < 1 or quantity > 99:
                        flash('Quantity must be between 1 and 99.', 'danger')
                        return render_template(
                            'edit_item.html',
                            item=item,
                            current_user=current_user,
                            status_choices=STATUS_CHOICES,
                            priority_choices=PRIORITY_CHOICES,
                            events=upcoming_events)
                    item.quantity = quantity
                except ValueError:
                    flash('Quantity must be a valid number.', 'danger')
                    return render_template(
                        'edit_item.html',
                        item=item,
                        current_user=current_user,
                        status_choices=STATUS_CHOICES,
                        priority_choices=PRIORITY_CHOICES,
                        events=upcoming_events)
            else:
                item.quantity = None

            db.session.commit()
            flash('Item updated successfully.', 'success')
            return redirect(get_items_url_with_filters())

    return render_template(
        'edit_item.html',
        item=item,
        current_user=current_user,
        status_choices=STATUS_CHOICES,
        priority_choices=PRIORITY_CHOICES,
        events=upcoming_events)


@bp.route('/claim_item/<int:item_id>', methods=['POST'])
@login_required
def claim_item(item_id):
    """Claim an item for purchase."""
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)

    if item.user_id == current_user.id:
        flash('You cannot claim your own item.', 'warning')
        return redirect(get_items_url_with_filters())

    if item.status != 'Available':
        flash('This item is no longer available to claim.', 'warning')
        return redirect(get_items_url_with_filters())

    item.status = 'Claimed'
    item.last_updated_by_id = current_user.id
    db.session.commit()

    # For htmx requests, return the updated item card
    if request.headers.get('HX-Request'):
        context = request.args.get('context')
        if context == 'dashboard':
            flash(f'You have claimed "{item.description}".', 'success')
            card_html = render_template(
                'partials/_dashboard_item_card.html', item=item)
            flash_html = render_template('partials/_flash_messages.html')
            return card_html + flash_html

        default_image_url = (
            'https://via.placeholder.com/600x400?text=Wishlist+Item'
        )
        return render_template(
            'partials/_item_card.html',
            item=item,
            default_image_url=default_image_url)

    flash(f'You have claimed "{item.description}".', 'success')
    return redirect(get_items_url_with_filters())


@bp.route('/unclaim_item/<int:item_id>', methods=['POST'])
@login_required
def unclaim_item(item_id):
    """Unclaim an item back to Available status."""
    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)

    # Allow unclaim if it's Claimed and the current user was the last to
    # update it (the claimer)
    if item.status == 'Claimed' and item.last_updated_by_id == current_user.id:
        item.status = 'Available'
        item.last_updated_by_id = current_user.id
        db.session.commit()

        if request.headers.get('HX-Request'):
            context = request.args.get('context')
            if context == 'dashboard':
                flash(f'You have unclaimed "{item.description}".', 'info')
                card_html = render_template(
                    'partials/_dashboard_item_card.html', item=item)
                flash_html = render_template('partials/_flash_messages.html')
                return card_html + flash_html

            default_image_url = (
                'https://via.placeholder.com/600x400?text=Wishlist+Item'
            )
            return render_template(
                'partials/_item_card.html',
                item=item,
                default_image_url=default_image_url)

        flash(f'You have unclaimed "{item.description}".', 'info')
    else:
        flash('You cannot unclaim this item.', 'danger')

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
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)

    default_image_url = (
        'https://via.placeholder.com/600x400?text=Wishlist+Item'
    )
    return render_template(
        'partials/_split_modal.html',
        item=item,
        default_image_url=default_image_url)


@bp.route('/item/<int:item_id>/refresh-price', methods=['POST'])
@login_required
def refresh_price(item_id):
    """Refresh the price for an item by fetching from its URL."""
    from services.price_service import refresh_item_price

    item = db.session.get(Item, item_id)
    if item is None:
        abort(404)

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
            flash(
                'Amazon blocks automated price fetching. '
                'You can update the price manually by editing the item.',
                'warning')
        else:
            flash(
                'Could not fetch price automatically. '
                'You can update it manually by editing the item.',
                'warning')

    return redirect(get_items_url_with_filters())


@bp.route('/delete_item/<int:item_id>')
@login_required
def delete_item(item_id):
    """Delete an item (owner only)."""
    item = db.session.get(Item, item_id)
    if item is None or item.user_id != current_user.id:
        flash('You do not have permission to delete this item.', 'danger')
        return redirect(get_items_url_with_filters())

    db.session.delete(item)
    db.session.commit()
    flash('Item deleted.', 'info')
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
        group = grouped_items.setdefault(
            item.user_id, SimpleNamespace(
                user=item.user, items=[]))
        group.items.append(item)

    # Count of claimed (not yet purchased) items for the badge
    claimed_count = sum(1 for item in items if item.status == 'Claimed')
    purchased_count = sum(1 for item in items if item.status == 'Purchased')

    default_image_url = (
        'https://via.placeholder.com/600x400?text=Wishlist+Item'
    )

    return render_template(
        'my_claims.html',
        grouped_items=list(grouped_items.values()),
        claimed_count=claimed_count,
        purchased_count=purchased_count,
        status_choices=STATUS_CHOICES,
        default_image_url=default_image_url,
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
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)

    if item.user_id == current_user.id:
        flash('You cannot split your own item.', 'warning')
        return redirect(get_items_url_with_filters())

    if item.status != 'Available':
        flash('Item is not available for splitting.', 'warning')
        return redirect(get_items_url_with_filters())

    # Get amount from form
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        flash('Invalid contribution amount.', 'danger')
        return redirect(get_items_url_with_filters())

    if amount <= 0:
        flash('Contribution amount must be positive.', 'danger')
        return redirect(get_items_url_with_filters())

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
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)

    if item.status != 'Splitting':
        flash('Item is not currently being split.', 'warning')
        return redirect(get_items_url_with_filters())

    # Check if already contributing
    existing = Contribution.query.filter_by(
        item_id=item.id, user_id=current_user.id).first()
    if existing:
        flash('You are already contributing to this split.', 'warning')
        return redirect(get_items_url_with_filters())

    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        flash('Invalid contribution amount.', 'danger')
        return redirect(get_items_url_with_filters())

    if amount <= 0:
        flash('Contribution amount must be positive.', 'danger')
        return redirect(get_items_url_with_filters())

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
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)

    contribution = Contribution.query.filter_by(
        item_id=item.id, user_id=current_user.id).first()
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
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)

    contribution = Contribution.query.filter_by(
        item_id=item.id, user_id=current_user.id).first()

    if not contribution or not contribution.is_organizer:
        flash('Only the split organizer can mark this as purchased.', 'danger')
        return redirect(get_items_url_with_filters())

    item.status = 'Purchased'
    # Organizer gets the credit in last_updated_by
    item.last_updated_by_id = current_user.id
    db.session.commit()

    flash(
        f'"{item.description}" marked as purchased! '
        'All contributors will be notified.',
        'success')
    # TODO: Send notifications to other contributors

    return redirect(get_items_url_with_filters())
