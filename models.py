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
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
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
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))
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
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Item variants (size, color, quantity)
    size = db.Column(db.String(50), nullable=True)
    color = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Integer, nullable=True)

    comments = db.relationship('Comment', backref='item', lazy=True, cascade='all, delete-orphan')

    # Composite index for common query pattern (user_id + status)
    __table_args__ = (
        db.Index('idx_item_user_status', 'user_id', 'status'),
    )

    @property
    def is_splitting(self):
        return self.status == 'Splitting'

    @property
    def total_pledged(self):
        return sum(c.amount for c in self.contributions)

    @property
    def split_progress(self):
        if not self.price or self.price == 0:
            return 0
        return min(100, int((self.total_pledged / self.price) * 100))

    @property
    def remaining_amount(self):
        if not self.price:
            return 0
        return max(0, self.price - self.total_pledged)

    @property
    def organizer(self):
        for c in self.contributions:
            if c.is_organizer:
                return c.user
        return None

    def __repr__(self):
        return f'<Item {self.description[:30]}...>'


class Comment(db.Model):
    """Comment model for item discussions."""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
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
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    recipient = db.relationship('User', backref='notifications')

    __table_args__ = (
        db.Index('idx_notif_user_unread', 'user_id', 'is_read'),
    )

    def __repr__(self):
        return f'<Notification for User {self.user_id}>'


class Contribution(db.Model):
    """Tracks contributions to split gifts."""
    __tablename__ = 'contributions'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    is_organizer = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    # Relationships
    item = db.relationship('Item', backref=db.backref('contributions', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref='contributions')

    __table_args__ = (
        db.UniqueConstraint('item_id', 'user_id', name='unique_contribution'),
    )

    def __repr__(self):
        return f'<Contribution {self.amount} by User {self.user_id} for Item {self.item_id}>'


class PriceExtractionLog(db.Model):
    """Log of price extraction attempts for monitoring and debugging."""
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(255), nullable=False, index=True)
    url = db.Column(db.String(2048))
    success = db.Column(db.Boolean, nullable=False)
    price = db.Column(db.Float, nullable=True)
    extraction_method = db.Column(db.String(50))  # 'meta', 'jsonld', 'selector', 'playwright'
    error_type = db.Column(db.String(50))  # 'captcha', 'timeout', 'no_price', 'blocked'
    response_time_ms = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)

    def __repr__(self):
        return f'<PriceLog {self.domain} Success={self.success}>'
class PriceHistory(db.Model):
    """Track historical prices for items to show trends."""
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)
    source = db.Column(db.String(50), default='auto')  # 'auto', 'manual', 'initial'

    # Relationship to Item
    item = db.relationship('Item', backref=db.backref('price_history', lazy=True, cascade='all, delete-orphan'))

    __table_args__ = (
        db.Index('idx_price_history_item_date', 'item_id', 'recorded_at'),
    )

    def __repr__(self):
        return f'<PriceHistory Item={self.item_id} Price={self.price} Date={self.recorded_at}>'
