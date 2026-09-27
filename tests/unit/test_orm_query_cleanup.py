"""Query-budget regressions and compatibility checks for the core ORM cleanup."""
from contextlib import contextmanager
import datetime
import re

import pytest
from flask import render_template
from flask_login import login_user
from sqlalchemy import event

from models import db, User, Item, Notification, Comment, Contribution


@contextmanager
def queries():
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().lower().startswith('select'):
            statements.append(' '.join(statement.lower().split()))

    engine = db.engine
    event.listen(engine, 'before_cursor_execute', record)
    try:
        yield statements
    finally:
        event.remove(engine, 'before_cursor_execute', record)


def counts(statements, table):
    return [s for s in statements if 'count(' in s and
            re.search(r'\bfrom ' + table + r'\b', s)]


def badge(html, href):
    link = re.search(r'<a\b[^>]*href="' + re.escape(href) + r'"[^>]*>(.*?)</a>',
                     html, re.S)
    assert link, html
    number = re.search(r'class="sidebar-badge">\s*(\d+)', link.group(1))
    return int(number.group(1)) if number else 0


def item(owner, claimer=None, status='Available', **kwargs):
    obj = Item(description='Query fixture', user_id=owner,
               last_updated_by_id=claimer, status=status, **kwargs)
    db.session.add(obj)
    db.session.commit()
    return obj


@pytest.mark.parametrize('template', ['partials/_flash_messages.html',
                                      'partials/_dashboard_item_card.html'])
def test_fragments_do_not_query_navigation(app, user, other_user, template):
    # @spec VW-UI-006, GIV-CLM-010
    obj = item(other_user)
    with app.test_request_context('/'):
        login_user(db.session.get(User, user))
        with queries() as sql:
            render_template(template, item=obj)
        assert not counts(sql, 'item')
        assert not counts(sql, 'notification')


def test_anonymous_sidebar_does_not_query_badges(app):
    # @spec VW-UI-008
    with app.test_request_context('/'):
        with queries() as sql:
            render_template('partials/_sidebar.html')
        assert not counts(sql, 'item')
        assert not counts(sql, 'notification')


def test_archived_claim_is_not_in_badge(app, client, login, user, other_user):
    # @spec GIV-CLM-009, GIV-CLM-012
    item(other_user, user, 'Claimed', archived_at=datetime.datetime.now(datetime.timezone.utc))
    item(user, user, 'Claimed')
    item(other_user, user, 'Purchased')
    response = client.get('/notifications')
    assert response.status_code == 200
    assert badge(response.text, '/my-claims') == 0


def test_dashboard_reuses_one_status_aggregate(app, client, login, user, other_user):
    # @spec GIV-CLM-012, GIV-CLM-013, GIV-CLM-016
    item(other_user, user, 'Claimed')
    item(other_user, user, 'Purchased')
    with queries() as sql:
        response = client.get('/')
    assert response.status_code == 200
    assert badge(response.text, '/my-claims') == 1
    assert len(counts(sql, 'item')) == 1
    assert 'group by' in counts(sql, 'item')[0]
    with queries() as cached_sql:
        assert client.get('/').status_code == 200
    assert not counts(cached_sql, 'item')


@pytest.mark.parametrize('populated', [False, True])
def test_complete_lists_seed_badges(app, client, login, user, other_user, populated):
    # @spec GIV-CLM-014, VW-UI-007, VW-UI-010
    if populated:
        item(other_user, user, 'Claimed')
        db.session.add(Notification(user_id=user, message='Unread', link='/'))
        db.session.commit()
    with queries() as sql:
        claims = client.get('/my-claims')
    assert claims.status_code == 200
    assert badge(claims.text, '/my-claims') == int(populated)
    assert not counts(sql, 'item')
    with queries() as sql:
        notifications = client.get('/notifications')
    assert notifications.status_code == 200
    assert badge(notifications.text, '/notifications') == int(populated)
    assert not counts(sql, 'notification')


def test_badge_reuse_is_request_local(app, user, other_user):
    # @spec VW-UI-007, VW-UI-009, GIV-CLM-013
    item(other_user, user, 'Claimed')
    for _ in range(2):
        with app.test_request_context('/'):
            login_user(db.session.get(User, user))
            with queries() as sql:
                first = render_template('partials/_sidebar.html')
                second = render_template('partials/_sidebar.html')
            assert badge(first, '/my-claims') == badge(second, '/my-claims') == 1
            assert len(counts(sql, 'item')) == 1
            assert len(counts(sql, 'notification')) == 1


def test_badge_invalidates_after_mutation_and_rollback(app, user, other_user):
    # @spec GIV-CLM-015, VW-UI-011
    obj = item(other_user, user, 'Claimed')
    notification = Notification(user_id=user, message='Unread', link='/')
    db.session.add(notification)
    db.session.commit()
    with app.test_request_context('/'):
        login_user(db.session.get(User, user))
        assert badge(render_template('partials/_sidebar.html'), '/my-claims') == 1
        obj.archived_at = datetime.datetime.now(datetime.timezone.utc)
        notification.is_read = True
        db.session.flush()
        html = render_template('partials/_sidebar.html')
        assert badge(html, '/my-claims') == 0
        assert badge(html, '/notifications') == 0
        db.session.rollback()
        html = render_template('partials/_sidebar.html')
        assert badge(html, '/my-claims') == 1
        assert badge(html, '/notifications') == 1
        Notification.query.filter_by(user_id=user).update({'is_read': True})
        assert badge(render_template('partials/_sidebar.html'), '/notifications') == 0
        db.session.rollback()


def test_list_does_not_join_independent_collections(app, client, login, user, other_user):
    # @spec VW-FEED-009, VW-FEED-010
    obj = item(other_user, status='Splitting', price=100)
    db.session.add_all([
        Comment(item_id=obj.id, user_id=user, text='A'),
        Comment(item_id=obj.id, user_id=user, text='B'),
        Contribution(item_id=obj.id, user_id=user, amount=10, is_organizer=True),
        Contribution(item_id=obj.id, user_id=other_user, amount=20),
    ])
    db.session.commit()
    with queries() as sql:
        response = client.get('/items')
    assert response.status_code == 200
    assert not any('join comment' in s and 'join contributions' in s for s in sql)
    assert any('from comment' in s and ' in (' in s for s in sql)
    assert any('from contributions' in s and ' in (' in s for s in sql)


def test_export_eagerly_loads_owners(app, client, login, other_user, tmp_path, monkeypatch):
    # @spec VW-FEED-011
    item(other_user)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app, "root_path", str(tmp_path))
    with queries() as sql:
        response = client.get('/export_items')
    assert response.status_code == 200
    item_queries = [s for s in sql if re.search(r'\bfrom item\b', s)]
    assert len(item_queries) == 1
    assert 'join user' in item_queries[0]
    response.close()


def test_model_timestamp_columns_and_split_values(app, user, other_user):
    # @spec VW-FEED-012, VW-FEED-013, VW-FEED-014
    columns = [t.c.created_at for t in db.metadata.tables.values() if 'created_at' in t.c]
    assert len({id(c) for c in columns}) == len(columns)
    assert all(c.default is not None and c.default.is_callable for c in columns)
    for model in (User, Item):
        assert model.__table__.c.updated_at.onupdate.is_callable
    before = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    obj = item(other_user)
    assert obj.created_at >= before
    assert obj.split_progress == 0
    obj.price = 0
    assert obj.split_progress == 0
    obj.price = 100
    db.session.add(Contribution(item_id=obj.id, user_id=user, amount=150, is_organizer=True))
    db.session.flush()
    assert obj.total_pledged == 150
    assert obj.split_progress == 100
    assert obj.remaining_amount == 0
    obj.price_fail_streak = 3
    obj.price_backoff_until = datetime.datetime.now(datetime.timezone.utc)
    db.session.commit()
    obj.link = 'https://example.com/new'
    db.session.flush()
    assert obj.price_fail_streak == 0
    assert obj.price_backoff_until is None


def test_reused_badges_are_isolated_by_viewer(app, user, other_user):
    # @spec VW-UI-009
    item(other_user, user, 'Claimed')
    with app.test_request_context('/'):
        login_user(db.session.get(User, user))
        assert badge(render_template('partials/_sidebar.html'), '/my-claims') == 1
        login_user(db.session.get(User, other_user))
        assert badge(render_template('partials/_sidebar.html'), '/my-claims') == 0


def test_completed_split_counts_once_for_organizer(app, client, login, user, other_user):
    # @spec GIV-CLM-012, GIV-CLM-017
    obj = item(other_user, user, 'Purchased', price=100)
    db.session.add(Contribution(item_id=obj.id, user_id=user, amount=50, is_organizer=True))
    db.session.commit()
    from flask import template_rendered
    contexts = []

    def capture(sender, template, context, **extra):
        contexts.append(context)

    template_rendered.connect(capture, app)
    try:
        with queries() as sql:
            response = client.get('/my-claims')
        assert response.status_code == 200
        context = contexts[-1]
        assert context['purchased_count'] == 1
        assert context['claimed_count'] == 0
        assert len(context['contributions']) == 1
        assert not any('join contributions' in s for s in sql)
    finally:
        template_rendered.disconnect(capture, app)


@pytest.mark.parametrize('change', ['status', 'owner', 'claimer', 'delete', 'insert'])
def test_claim_cache_tracks_population_changes(app, user, other_user, change):
    # @spec GIV-CLM-015
    obj = item(other_user, user, 'Claimed')
    with app.test_request_context('/'):
        login_user(db.session.get(User, user))
        assert badge(render_template('partials/_sidebar.html'), '/my-claims') == 1
        if change == 'status':
            obj.status = 'Purchased'
        elif change == 'owner':
            obj.user_id = user
        elif change == 'claimer':
            obj.last_updated_by_id = other_user
        elif change == 'delete':
            db.session.delete(obj)
        else:
            db.session.add(Item(description='New claim', user_id=other_user,
                                last_updated_by_id=user, status='Claimed'))
        # No explicit flush: reading a memoized count must see pending writes.
        assert badge(render_template('partials/_sidebar.html'), '/my-claims') == (
            2 if change == 'insert' else 0)
        db.session.rollback()


def test_notification_cache_tracks_recipient_and_bulk_delete(app, user, other_user):
    # @spec VW-UI-011
    obj = Notification(user_id=user, message='Unread', link='/')
    db.session.add(obj)
    db.session.commit()
    with app.test_request_context('/'):
        login_user(db.session.get(User, user))
        assert badge(render_template('partials/_sidebar.html'), '/notifications') == 1
        login_user(db.session.get(User, other_user))
        assert badge(render_template('partials/_sidebar.html'), '/notifications') == 0
        obj.user_id = other_user
        assert badge(render_template('partials/_sidebar.html'), '/notifications') == 1
        login_user(db.session.get(User, user))
        assert badge(render_template('partials/_sidebar.html'), '/notifications') == 0
        Notification.query.delete()
        login_user(db.session.get(User, other_user))
        assert badge(render_template('partials/_sidebar.html'), '/notifications') == 0
        db.session.rollback()
