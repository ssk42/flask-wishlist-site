"""Regression coverage for the release-critical wishlist management journey."""

import re

import pytest

from models import Item, db


def _login(client):
    return client.post('/login', data={'email': 'test@example.com', 'password': 'testsecret'})


def _form_token(response):
    match = re.search(rb'name="submission_token" value="([^"]+)"', response.data)
    assert match, 'item forms must include an idempotency token'
    return match.group(1).decode()


def _create(client, description, **extra):
    page = client.get('/submit_item')
    data = {'description': description, 'priority': 'Low', 'status': 'Available',
            'submission_token': _form_token(page), **extra}
    return client.post('/submit_item', data=data, follow_redirects=False)


def test_create_is_idempotent_and_survives_reload(client, app, login):
    page = client.get('/submit_item')
    token = _form_token(page)
    data = {'description': 'One-time tent', 'priority': 'High', 'status': 'Available',
            'submission_token': token}

    assert client.post('/submit_item', data=data).status_code == 302
    duplicate = client.post('/submit_item', data=data, follow_redirects=True)

    assert b'already added' in duplicate.data
    with app.app_context():
        assert Item.query.filter_by(description='One-time tent').count() == 1
    assert b'One-time tent' in client.get('/items').data


def test_invalid_edit_preserves_unsaved_values_and_database_state(client, app, login, user):
    with app.app_context():
        item = Item(description='Original', priority='Low', status='Available', user_id=user)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    token = _form_token(client.get(f'/edit_item/{item_id}'))
    response = client.post(f'/edit_item/{item_id}', data={
        'description': 'Unsaved replacement', 'category': 'Camping', 'price': '-1',
        'priority': 'High', 'submission_token': token,
    })

    assert response.status_code == 200
    assert b'Price cannot be negative' in response.data
    assert b'value="Unsaved replacement"' in response.data
    assert b'value="Camping"' in response.data
    with app.app_context():
        assert db.session.get(Item, item_id).description == 'Original'


def test_create_rejects_an_invalid_link_without_losing_input(client, login):
    page = client.get('/submit_item')
    response = client.post('/submit_item', data={
        'description': 'Keep my draft', 'link': 'javascript:alert(1)',
        'priority': 'Low', 'status': 'Available', 'submission_token': _form_token(page),
    })

    assert response.status_code == 200
    assert b'Link must be a valid http or https URL' in response.data
    assert b'value="Keep my draft"' in response.data


def test_edit_failure_is_recoverable(client, app, login, user, monkeypatch):
    with app.app_context():
        item = Item(description='Before outage', priority='Low', status='Available', user_id=user)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    token = _form_token(client.get(f'/edit_item/{item_id}'))
    monkeypatch.setattr(db.session, 'commit', lambda: (_ for _ in ()).throw(RuntimeError('database offline')))
    response = client.post(f'/edit_item/{item_id}', data={
        'description': 'Keep this edit', 'priority': 'Low', 'submission_token': token,
    })

    assert response.status_code == 200
    assert b'Failed to update item' in response.data
    assert b'value="Keep this edit"' in response.data


def test_consecutive_create_edit_delete_keeps_sorted_list_consistent(client, app, login, user):
    assert _create(client, 'Bravo').status_code == 302
    assert _create(client, 'Alpha').status_code == 302
    with app.app_context():
        bravo = Item.query.filter_by(description='Bravo').one()
        alpha = Item.query.filter_by(description='Alpha').one()
        bravo_id, alpha_id = bravo.id, alpha.id

    token = _form_token(client.get(f'/edit_item/{bravo_id}'))
    assert client.post(f'/edit_item/{bravo_id}', data={
        'description': 'Charlie', 'priority': 'Low', 'submission_token': token,
    }).status_code == 302
    assert client.post(f'/delete_item/{alpha_id}').status_code == 302

    response = client.get('/items?sort_by=description&sort_order=asc')
    assert b'Charlie' in response.data
    assert b'Alpha' not in response.data
    with app.app_context():
        assert db.session.get(Item, alpha_id) is None
        assert db.session.get(Item, bravo_id).description == 'Charlie'


def test_delete_requires_post_and_recovers_from_a_failed_commit(client, app, login, user, monkeypatch):
    with app.app_context():
        item = Item(description='Do not lose me', priority='Low', status='Available', user_id=user)
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    assert client.get(f'/delete_item/{item_id}').status_code == 405
    monkeypatch.setattr(db.session, 'commit', lambda: (_ for _ in ()).throw(RuntimeError('database offline')))
    response = client.post(f'/delete_item/{item_id}', follow_redirects=True)
    assert b'Failed to delete item' in response.data
    with app.app_context():
        assert db.session.get(Item, item_id) is not None
