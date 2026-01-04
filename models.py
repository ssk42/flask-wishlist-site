"""Database models for the Wishlist application."""

import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy instance - initialized in app.py and passed here
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication and ownership."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    is_private = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    items = db.relationship('Item', backref='user', lazy=True, foreign_keys='Item.user_id')

    @property
    def unread_count(self):
        """Count of unread notifications for this user."""
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

    def __repr__(self):
        return f'<User {self.name}>'


class Event(db.Model):
    """Event model for gift-giving occasions."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reminder_sent = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    created_by = db.relationship('User', backref='events')
    items = db.relationship('Item', backref='event', lazy=True)

    def __repr__(self):
        return f'<Event {self.name} ({self.date})>'


class Item(db.Model):
    """Wishlist item model."""
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(750), nullable=False)
    link = db.Column(db.String(2048), nullable=True)
    comment = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Available', index=True)
    question = db.Column(db.String(100))
    year = db.Column(db.Integer, default=datetime.datetime.now().year)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    category = db.Column(db.String(50), index=True)
    image_url = db.Column(db.String(2048))
    priority = db.Column(db.String(50), index=True)
    last_updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_updated_by = db.relationship('User', foreign_keys=[last_updated_by_id])
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True, index=True)
    price_updated_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    comments = db.relationship('Comment', backref='item', lazy=True, cascade='all, delete-orphan')

    # Composite index for common query pattern (user_id + status)
    __table_args__ = (
        db.Index('idx_item_user_status', 'user_id', 'status'),
    )

    def __repr__(self):
        return f'<Item {self.description[:30]}...>'


class Comment(db.Model):
    """Comment model for item discussions."""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)

    # Author relationship
    author = db.relationship('User', backref='comments')

    __table_args__ = (
        db.Index('idx_comment_item', 'item_id', 'created_at'),
    )

    def __repr__(self):
        return f'<Comment by User {self.user_id} on Item {self.item_id}>'


class Notification(db.Model):
    """Notification model for user alerts."""
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    recipient = db.relationship('User', backref='notifications')

    __table_args__ = (
        db.Index('idx_notif_user_unread', 'user_id', 'is_read'),
    )

    def __repr__(self):
        return f'<Notification for User {self.user_id}>'
