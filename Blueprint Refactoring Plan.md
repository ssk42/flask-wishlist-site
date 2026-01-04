# Blueprint Refactoring Plan

## Overview

Refactor the monolithic 1,083-line app.py into 6 logical blueprints while maintaining all functionality and test coverage.

## Progress Summary

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Foundation | ✅ COMPLETE | models.py, config.py, services/utils.py created |
| Phase 2: App Factory | ✅ COMPLETE | app.py refactored to use create_app() |
| Phase 3: Blueprints | ✅ COMPLETE | All 6 blueprints created |
| Phase 4: app.py cleanup | ✅ COMPLETE | Reduced to ~170 lines |
| Phase 5: Update Tests | ✅ COMPLETE | Unit tests passed, browser tests environment pending |

## Target Structure

```
Wishlist/
├── app.py                    # App factory + extensions + CLI + context processors
├── models.py                 # All 5 models (User, Event, Item, Comment, Notification)
├── config.py                 # Already exists - add constants
├── blueprints/
│   ├── __init__.py
│   ├── auth.py               # 4 routes: register, login, logout, forgot_email
│   ├── dashboard.py          # 2 routes: index, export_items
│   ├── items.py              # 9 routes: items, submit, edit, claim, unclaim, delete, modal, refresh-price, my-claims
│   ├── events.py             # 4 routes: events, new, edit, delete
│   ├── social.py             # 3 routes: comment, notifications, mark_read
│   └── api.py                # 1 route: fetch-metadata
├── services/                 # Already exists
│   ├── utils.py              # NEW: get_items_url_with_filters()
│   └── ...
└── templates/                # Unchanged
```

## Implementation Phases

### Phase 1: Foundation (models.py, config.py, services/utils.py) ✅ COMPLETE

1. ✅ Create models.py - Extract all 5 models from app.py
   - User, Event, Item, Comment, Notification
   - db = SQLAlchemy() defined in models.py, init_app() called in create_app()
2. ✅ Update config.py - Add constants
   - PRIORITY_CHOICES = ['High', 'Medium', 'Low']
   - STATUS_CHOICES = ['Available', 'Claimed', 'Purchased', 'Received']
3. ✅ Create services/utils.py - Extract helper
   - get_items_url_with_filters() function

### Phase 2: Create App Factory ✅ COMPLETE

Updated app.py to use factory pattern:
```python
def create_app(config_name=None):
    app = Flask(__name__)
    # Load config
    # Initialize extensions
    # Register blueprints
    # Register context processors
    # Register CLI commands
    return app

# For backwards compatibility
app = create_app()
```

### Phase 3: Extract Blueprints (in order of complexity) ✅ COMPLETE

#### 3a. auth.py (4 routes) ✅ COMPLETE

- /register (GET, POST)
- /login (GET, POST)
- /logout (POST)
- /forgot_email (GET, POST)

Dependencies: User model, login_manager, db

#### 3b. api.py (1 route) ✅ COMPLETE

- /api/fetch-metadata (POST)

Dependencies: price_service

#### 3c. dashboard.py (2 routes) ✅ COMPLETE

- / (GET) - index
- /export_items (GET)

Dependencies: Item, Event, User models, pandas

#### 3d. events.py (4 routes) ✅ COMPLETE

- /events (GET)
- /events/new (GET, POST)
- /events/<id>/edit (GET, POST)
- /events/<id>/delete (POST)

Dependencies: Event, Item, User models

#### 3e. social.py (3 routes) ✅ COMPLETE

- /item/<id>/comment (POST)
- /notifications (GET)
- /notifications/read/<id> (POST)

Dependencies: Item, Comment, User, Notification models

#### 3f. items.py (10 routes) ✅ COMPLETE

- /items (GET) - complex filtering/sorting
- /submit_item (GET, POST)
- /edit_item/<id> (GET, POST)
- /claim_item/<id> (POST)
- /unclaim_item/<id> (POST)
- /delete_item/<id> (GET)
- /items/<id>/modal (GET)
- /item/<id>/refresh-price (POST)
- /my-claims (GET)
- /export_my_status_updates (GET)

Dependencies: All models, utils, price_service

### Phase 4: Keep in app.py ✅ COMPLETE

These remain in the main app.py:
- ✅ App factory function
- ✅ Extension initialization (db, csrf, mail, login_manager, compress, etc.)
- ✅ Context processors (inject_notifications, inject_claimed_count)
- ✅ After-request handler (set_security_headers)
- ✅ CLI commands (send-reminders, update-prices)
- ✅ Login manager user_loader

### Phase 5: Update Tests ✅ COMPLETE

- ✅ Update imports in test files to use new module paths (models.py, config.py)
- ✅ Update template url_for() calls to use blueprint prefixes
  - ✅ base.html
  - ✅ partials/_sidebar.html
  - ✅ index.html
  - ✅ items_list.html
  - ✅ submit_item.html
  - ✅ edit_item.html
  - ✅ my_claims.html
  - ✅ login.html
  - ✅ registration.html
  - ✅ forgot_email.html
  - ✅ events.html
  - ✅ event_form.html
  - ✅ partials/_item_card.html
  - ✅ partials/_dashboard_item_card.html
  - ✅ partials/_item_quick_view.html
  - ✅ notifications.html
- ✅ Run full test suite to verify (Unit tests passed)

## Files Created

| File                    | Status | Lines | Content                        |
|-------------------------|--------|-------|--------------------------------|
| models.py               | ✅     | ~150  | 5 models extracted from app.py |
| blueprints/__init__.py  | ✅     | ~10   | Package init with imports      |
| blueprints/auth.py      | ✅     | ~90   | 4 auth routes                  |
| blueprints/api.py       | ✅     | ~25   | 1 API route                    |
| blueprints/dashboard.py | ✅     | ~75   | 2 dashboard routes             |
| blueprints/events.py    | ✅     | ~125  | 4 event routes                 |
| blueprints/social.py    | ✅     | ~70   | 3 social routes                |
| blueprints/items.py     | ✅     | ~450  | 10 item routes (most complex)  |
| services/utils.py       | ✅     | ~30   | Helper functions               |

## Files Modified

| File       | Status | Changes                                                             |
|------------|--------|---------------------------------------------------------------------|
| app.py     | ✅     | Reduced to ~170 lines (factory, extensions, CLI, context processors) |
| config.py  | ✅     | Added PRIORITY_CHOICES, STATUS_CHOICES                               |
| tests/*.py | ✅     | Updated imports to use models.py and config.py                       |
| templates/ | 🔄     | Updating url_for() calls to use blueprint prefixes                   |

## Key Dependencies Maintained

1. ✅ Filter persistence: get_items_url_with_filters() importable by items.py
2. ✅ Login protection: @login_required decorator on protected routes
3. ✅ CSRF protection: Forms include csrf_token
4. ✅ Context processors: Run for all blueprints (navbar badges)
5. ✅ Security headers: Apply to all responses

## Remaining Work

1. Update remaining template url_for() calls:
   - events.html, event_form.html
   - partials/_item_card.html, _dashboard_item_card.html, _item_quick_view.html
   - notifications.html
2. Run full test suite
3. Fix any remaining issues

## Route Name Mapping (for template updates)

| Old Name | New Blueprint Name |
|----------|-------------------|
| `index` | `dashboard.index` |
| `items` | `items.items_list` |
| `submit_item` | `items.submit_item` |
| `edit_item` | `items.edit_item` |
| `delete_item` | `items.delete_item` |
| `claim_item` | `items.claim_item` |
| `unclaim_item` | `items.unclaim_item` |
| `my_claims` | `items.my_claims` |
| `export_my_status_updates` | `items.export_my_status_updates` |
| `get_item_modal` | `items.get_item_modal` |
| `refresh_price` | `items.refresh_price` |
| `events` | `events.events_list` |
| `new_event` | `events.new_event` |
| `edit_event` | `events.edit_event` |
| `delete_event` | `events.delete_event` |
| `login` | `auth.login` |
| `logout` | `auth.logout` |
| `register` | `auth.register` |
| `forgot_email` | `auth.forgot_email` |
| `notifications` | `social.notifications` |
| `add_comment` | `social.add_comment` |
