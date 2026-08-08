"""JSON serializers for API v1.

SURPRISE PROTECTION IS ENFORCED HERE, server-side: an item owner's
serialization NEVER includes claim data ('status', 'last_updated_by'),
so no client — or curl — can reveal who claimed a gift to its owner.
"""


def serialize_user(user, item_count=None):
    data = {'id': user.id, 'name': user.name, 'email': user.email}
    if item_count is not None:
        data['item_count'] = item_count
    return data


def serialize_item(item, viewer):
    """Serialize an item as seen by `viewer` (a User)."""
    data = {
        'id': item.id,
        'description': item.description,
        'link': item.link,
        'price': item.price,
        'category': item.category,
        'image_url': item.image_url,
        'priority': item.priority,
        'event_id': item.event_id,
        'size': item.size,
        'color': item.color,
        'quantity': item.quantity,
        'user_id': item.user_id,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'updated_at': item.updated_at.isoformat() if item.updated_at else None,
    }
    if item.user_id != viewer.id:
        data['status'] = item.status
        claimer = item.last_updated_by
        data['last_updated_by'] = (
            {'id': claimer.id, 'name': claimer.name} if claimer else None
        )
    return data


def serialize_notification(notification):
    return {
        'id': notification.id,
        'message': notification.message,
        'link': notification.link,
        'is_read': notification.is_read,
        'created_at': notification.created_at.isoformat() if notification.created_at else None,
    }
