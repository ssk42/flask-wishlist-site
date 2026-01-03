Blueprint Refactoring Plan

 Overview

 Refactor the monolithic 1,083-line app.py into 6 logical blueprints while maintaining all functionality and test coverage.

 Target Structure

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

 Implementation Phases

 Phase 1: Foundation (models.py, config.py, services/utils.py)

 1. Create models.py - Extract all 5 models from app.py
   - User, Event, Item, Comment, Notification
   - Keep db = SQLAlchemy() in app.py, import in models.py
 2. Update config.py - Add constants
   - PRIORITY_CHOICES = ['High', 'Medium', 'Low']
   - STATUS_CHOICES = ['Available', 'Claimed', 'Purchased', 'Received']
 3. Create services/utils.py - Extract helper
   - get_items_url_with_filters() function

 Phase 2: Create App Factory

 Update app.py to use factory pattern:
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

 Phase 3: Extract Blueprints (in order of complexity)

 3a. auth.py (4 routes) - Simplest

 - /register (GET, POST)
 - /login (GET, POST)
 - /logout (POST)
 - /forgot_email (GET, POST)

 Dependencies: User model, login_manager, db

 3b. api.py (1 route) - Trivial

 - /api/fetch-metadata (POST)

 Dependencies: price_service

 3c. dashboard.py (2 routes) - Simple

 - / (GET) - index
 - /export_items (GET)

 Dependencies: Item, Event, User models, pandas

 3d. events.py (4 routes) - Medium

 - /events (GET)
 - /events/new (GET, POST)
 - /events/<id>/edit (GET, POST)
 - /events/<id>/delete (POST)

 Dependencies: Event, Item, User models

 3e. social.py (3 routes) - Medium

 - /item/<id>/comment (POST)
 - /notifications (GET)
 - /notifications/read/<id> (POST)

 Dependencies: Item, Comment, User, Notification models

 3f. items.py (9 routes) - Most Complex

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

 Phase 4: Keep in app.py

 These remain in the main app.py:
 - App factory function
 - Extension initialization (db, csrf, mail, login_manager, compress, etc.)
 - Context processors (inject_notifications, inject_claimed_count)
 - After-request handler (set_security_headers)
 - CLI commands (send-reminders, update-prices)
 - Login manager user_loader

 Phase 5: Update Tests

 - Update imports in test files to use new module paths
 - Tests should continue to work since app factory returns same app

 Files to Create

 | File                    | Lines (est.) | Content                        |
 |-------------------------|--------------|--------------------------------|
 | models.py               | ~150         | 5 models extracted from app.py |
 | blueprints/init.py      | ~5           | Package init                   |
 | blueprints/auth.py      | ~80          | 4 auth routes                  |
 | blueprints/api.py       | ~25          | 1 API route                    |
 | blueprints/dashboard.py | ~100         | 2 dashboard routes             |
 | blueprints/events.py    | ~120         | 4 event routes                 |
 | blueprints/social.py    | ~80          | 3 social routes                |
 | blueprints/items.py     | ~400         | 10 item routes (most complex)  |
 | services/utils.py       | ~30          | Helper functions               |

 Files to Modify

 | File       | Changes                                                             |
 |------------|---------------------------------------------------------------------|
 | app.py     | Reduce to ~200 lines (factory, extensions, CLI, context processors) |
 | config.py  | Add PRIORITY_CHOICES, STATUS_CHOICES                                |
 | tests/*.py | Update imports if needed                                            |

 Key Dependencies to Maintain

 1. Filter persistence: get_items_url_with_filters() must be importable by items.py
 2. Login protection: @login_required decorator on protected routes
 3. CSRF protection: Forms must include csrf_token
 4. Context processors: Must run for all blueprints (navbar badges)
 5. Security headers: Must apply to all responses

 Execution Order

 1. Create models.py (extract models)
 2. Update config.py (add constants)
 3. Create services/utils.py (extract helper)
 4. Create blueprints/init.py
 5. Create blueprints/auth.py
 6. Create blueprints/api.py
 7. Create blueprints/dashboard.py
 8. Create blueprints/events.py
 9. Create blueprints/social.py
 10. Create blueprints/items.py (largest)
 11. Update app.py (factory pattern, register blueprints)
 12. Run tests to verify
 13. Fix any import issues

 Risk Mitigation

 - Run tests after each blueprint extraction
 - Keep app.py functional throughout (don't break existing routes until new ones work)
 - Maintain backwards compatibility with app = create_app() at module level