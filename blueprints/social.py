"""Social blueprint for comments and notifications."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from models import db, User, Item, Comment, Notification
from services.utils import get_items_url_with_filters

bp = Blueprint('social', __name__)


@bp.route('/item/<int:item_id>/comment', methods=['POST'])
@login_required
def add_comment(item_id):
    """Add a comment to an item."""
    item = Item.query.get_or_404(item_id)
    text = request.form.get('text', '').strip()

    if not text:
        flash('Comment cannot be empty.', 'warning')
        return redirect(get_items_url_with_filters())

    if item.user_id == current_user.id:
        flash('You cannot comment on your own wishlist item.', 'danger')
        return redirect(get_items_url_with_filters())

    # Add Comment
    comment = Comment(text=text, user_id=current_user.id, item_id=item.id)
    db.session.add(comment)

    # Generate Notifications
    # Notify other commenters on this item
    previous_commenters = db.session.query(User).join(Comment).filter(
        Comment.item_id == item_id,
        User.id != current_user.id,  # Don't notify self
        User.id != item.user_id      # Don't notify owner
    ).distinct().all()

    for recipient in previous_commenters:
        msg = f"{current_user.name} commented on an item for {item.user.name}: {item.description[:30]}..."
        link = url_for('items.items_list', _anchor=f'item-{item.id}')
        notif = Notification(user_id=recipient.id, message=msg, link=link)
        db.session.add(notif)

    db.session.commit()
    flash('Comment added!', 'success')
    return redirect(get_items_url_with_filters())


@bp.route('/notifications')
@login_required
def notifications():
    """List all notifications for the current user."""
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifs)


@bp.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    """Mark a notification as read."""
    notif = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})
    return redirect(url_for('social.notifications'))
