"""APNs push delivery (HTTP/2, .p8 token auth).

Feature-flagged: no-ops unless all APNS_* config values are set, so the
API and web app run fine without any Apple configuration.
"""

import datetime

import httpx
import jwt
from flask import current_app

from models import db, Device

APNS_HOST_PROD = 'https://api.push.apple.com'
APNS_HOST_SANDBOX = 'https://api.sandbox.push.apple.com'


def apns_enabled():
    cfg = current_app.config
    return bool(cfg.get('APNS_KEY_P8') and cfg.get('APNS_KEY_ID')
                and cfg.get('APNS_TEAM_ID') and cfg.get('APNS_BUNDLE_ID'))


def _apns_jwt():
    cfg = current_app.config
    now = datetime.datetime.now(datetime.timezone.utc)
    return jwt.encode(
        {'iss': cfg['APNS_TEAM_ID'], 'iat': int(now.timestamp())},
        cfg['APNS_KEY_P8'],
        algorithm='ES256',
        headers={'kid': cfg['APNS_KEY_ID']},
    )


def send_push_to_user(user_id, message, link=None, client=None):
    """Send `message` to all of the user's devices. Returns devices reached.

    `client` is injectable for tests; production uses a real httpx client.
    APNs 410 means the device token is dead — the row is deleted.
    """
    if not apns_enabled():
        return 0
    devices = Device.query.filter_by(user_id=user_id).all()
    if not devices:
        return 0

    cfg = current_app.config
    host = APNS_HOST_SANDBOX if cfg.get('APNS_USE_SANDBOX') else APNS_HOST_PROD
    headers = {
        'authorization': f'bearer {_apns_jwt()}',
        'apns-topic': cfg['APNS_BUNDLE_ID'],
        'apns-push-type': 'alert',
        'apns-priority': '10',
    }
    payload = {'aps': {'alert': {'title': 'Wishlist', 'body': message}, 'sound': 'default'}}
    if link:
        payload['link'] = link

    own_client = client is None
    if own_client:
        client = httpx.Client(http2=True, timeout=10)
    sent = 0
    try:
        for device in devices:
            try:
                response = client.post(f'{host}/3/device/{device.apns_token}',
                                       headers=headers, json=payload)
            except Exception as exc:
                current_app.logger.warning(f'APNs send failed for device {device.id}: {exc}')
                continue
            if response.status_code == 200:
                sent += 1
            elif response.status_code == 410:
                db.session.delete(device)
        db.session.commit()
    finally:
        if own_client:
            client.close()
    return sent
