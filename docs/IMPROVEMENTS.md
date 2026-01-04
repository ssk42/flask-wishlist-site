# Wishlist App Improvement Plan

This document tracks all planned and completed improvements to the Family Wishlist application.

**Last Updated:** 2026-01-04 (Session 7)

---

## 🎯 Quick Wins (30 min effort, high impact)

| # | Improvement | Priority | Status | Date Completed |
|---|-------------|----------|--------|----------------|
| 1 | CSRF Protection with Flask-WTF | 🔴 Critical | ✅ Complete | 2025-10-16 |
| 2 | Add Database Indexes | 🟡 High | ✅ Complete | 2025-10-16 |
| 3 | Security Headers | 🟡 High | ✅ Complete | 2025-10-16 |
| 4 | Extract CSS to Static File | 🟢 Medium | ✅ Complete | 2025-10-16 |
| 5 | Create .env.example | 🟢 Medium | ✅ Complete | 2025-10-16 |
| 6 | Add robots.txt | 🟢 Low | ✅ Complete | 2025-10-16 |



---

## 🏗️ Infrastructure Improvements

### Phase 1: Security & Infrastructure (High Priority)

| # | Improvement | Effort | Priority | Status | Date Completed | Notes |
|---|-------------|--------|----------|--------|----------------|-------|
| 7 | Docker Containerization | 2-3 hours | 🟡 High | ✅ Complete | 2025-10-16 | Multi-stage Dockerfile, docker-compose, Makefile |
| 8 | Environment Config Management | 1 hour | 🟡 High | ✅ Complete | 2025-10-16 | python-dotenv, config.py with env-based configs |
| 9 | Logging & Error Tracking | 1-2 hours | 🟡 High | ✅ Complete | 2025-10-16 | Structured JSON logging, request/error tracking |
| 10 | Proper Authentication | 4-6 hours | 🟡 High | ✅ Complete | 2026-01-04 | Shared Family Code (Simple + Secure) |
| 11 | Privacy Controls | 2-3 hours | 🟡 High | ⏳ Pending | - | Private wishlists, family groups, sharing |

### Phase 2: Performance & Reliability (Medium Priority)

| # | Improvement | Effort | Priority | Status | Notes |
|---|-------------|--------|----------|--------|-------|
| 12 | Caching Layer (Redis) | 2-3 hours | 🟢 Medium | ✅ Complete | 2026-01-04 | Cache dashboard stats |
| 13 | Database Connection Pooling | 30 min | 🟢 Medium | ✅ Complete | 2026-01-04 | SQLALCHEMY_ENGINE_OPTIONS |
| 14 | Add Timestamps | 1 hour | 🟢 Medium | ✅ Complete | 2026-01-04 | created_at, updated_at fields |
| 15 | Automated Backups | 1 hour | 🟢 Medium | ✅ Complete | 2026-01-04 | Heroku PG Backups at 02:00 UTC |
| 16 | Rate Limiting | 1 hour | 🟢 Low | ✅ Complete | 2026-01-03 | Flask-Limiter for API protection |
| 36 | Async Task Queue (Celery) | 3-4 hours | 🟡 High | ✅ Complete | 2026-01-04 | Celery with Redis broker |

### Phase 3: DevOps & CI/CD (Medium Priority)

| # | Improvement | Effort | Priority | Status | Date Completed | Notes |
|---|-------------|--------|----------|--------|----------------|-------|
| 17 | Enhanced CI Checks | 2 hours | 🟢 Medium | ✅ Complete | 2026-01-04 | flake8, bandit, safety |
| 18 | Deployment Automation | 2-3 hours | 🟢 Medium | ✅ Complete | 2026-01-04 | GitHub Actions + Heroku |
| 19 | Monitoring Dashboard | 3-4 hours | 🟢 Low | ✅ Complete | 2026-01-04 | Sentry + Heroku Metrics |

---

## 🏛️ Flask Architecture & Code Quality

### Flask Best Practices Audit (2026-01-03)

The following improvements were identified from a Flask best practices analysis. Currently the app follows ~65% of best practices.

| # | Improvement | Effort | Priority | Status | Date Completed | Notes |
|---|-------------|--------|----------|--------|-------|
| 37 | Refactor to Blueprints | 4-6 hours | 🔴 Critical | ✅ Complete | 2026-01-03 | Split 1,083-line app.py into logical modules |
| 38 | Application Factory Pattern | 2-3 hours | 🟡 High | ✅ Complete | 2026-01-03 | `create_app()` for better testing & config |
| 39 | Integrate config.py | 1 hour | 🟡 High | ✅ Complete | 2026-01-03 | config.py exists but isn't loaded |
| 40 | Global Error Handlers | 1-2 hours | 🟡 High | ✅ Complete | 2026-01-03 | Add 404/500 handlers with templates |
| 41 | Extract Models to models.py | 1-2 hours | 🟢 Medium | ✅ Complete | 2026-01-03 | Move 5 models out of app.py |
| 42 | Rate Limiting on Auth | 1 hour | 🟢 Medium | ✅ Complete | 2026-01-03 | Protect login/register endpoints |
| 43 | Configure Heroku Redis | 0.5 hours | 🟢 Medium | ✅ Complete | 2026-01-03 | Auto-configure Redis on Heroku |



---

## 🎨 User-Facing Improvements

### Phase 4: Core Features (High Priority)

| # | Feature | Effort | Priority | Status | Date Completed | Notes |
|---|---------|--------|----------|--------|----------------|-------|
| 20 | Email Notifications | 3-4 hours | 🟡 High | ✅ Complete | 2025-12-28 | Event reminders 7 days before |
| 21 | Image Upload | 3-4 hours | 🟢 Medium | ⏳ Pending | - | Direct upload to S3/Cloudinary |
| 22 | Wishlist Sharing Links | 2-3 hours | 🟡 High | ⏳ Pending | - | 📋 [PRD](PRD_WISHLIST_SHARING.md) - Public/private, guest access |
| 33 | My Claims Page | 2-3 hours | 🟡 High | ✅ Complete | 2025-12-28 | Track claimed/purchased items for others |
| 34 | Events Management | 3-4 hours | 🟡 High | ✅ Complete | 2025-12-28 | CRUD for events, item associations |
| 35 | Price Tracking | 2-3 hours | 🟢 Medium | ✅ Complete | 2025-12-28 | Auto-fetch prices, refresh buttons |

### Phase 5: Enhanced UX (Medium Priority)

| # | Feature | Effort | Priority | Status | Notes |
|---|---------|--------|----------|--------|-------|
| 23 | PWA Features | 4-6 hours | 🟢 Medium | ✅ Complete | 2026-01-04 | Manifest, Service Worker, Offline support |
| 24 | Advanced Search | 2-3 hours | 🟢 Low | ⏳ Pending | Fuzzy search, price range, multi-select |
| 25 | Item Variants | 2 hours | 🟢 Medium | ✅ Complete | 2026-01-04 | 📋 [PRD](PRD_ITEM_VARIANTS.md) - Size, color, quantity fields |
| 26 | Comments/Notes | 3-4 hours | 🟢 Medium | ✅ Complete | - | Collaboration on items (Added in previous sessions) |
| 27 | Accessibility (A11y) | 2-3 hours | 🟢 Medium | ⏳ Pending | ARIA labels, keyboard nav, screen readers |

### Phase 6: Nice to Have (Low Priority)

| # | Feature | Effort | Priority | Status | Notes |
|---|---------|--------|----------|--------|-------|
| 28 | Analytics Dashboard | 4-6 hours | 🟢 Low | ⏳ Pending | User insights, popular items |
| 29 | Export Enhancements | 2 hours | 🟢 Low | ⏳ Pending | PDF with images, CSV |
| 30 | Keyboard Shortcuts | 1-2 hours | 🟢 Low | ⏳ Pending | N for new, / for search |
| 31 | Internationalization | 6-8 hours | 🟢 Low | ⏳ Pending | Multi-language support |
| 32 | Split Gifts | 3-4 hours | 🟢 Low | ⏳ Pending | 📋 [PRD](PRD_SPLIT_GIFTS.md) - Multiple contributors |

### Phase 7: Advanced Features (New Ideas)

| # | Feature | Effort | Priority | Status | Notes |
|---|---------|--------|----------|--------|-------|
| 44 | **Image Hosting (R2)** | 4-6 hours | 🟡 High | ⏳ Pending | Cloudflare R2 for cheaper storage & globally served assets |
| 45 | **Multi-Tenant Support** | 20+ hours | 🔴 Critical | ⏳ Pending | Allow other families to sign up (SaaS) |
| 46 | **Wishlist Archive** | 2-3 hours | 🟢 Low | ⏳ Pending | "Soft delete" or archive old/fulfilled items |
| 47 | **External Share Links** | 3-4 hours | 🟡 High | ⏳ Pending | 📋 [PRD](PRD_WISHLIST_SHARING.md) - Public read-only link for non-family (Grammy/friends) |
| 48 | **Gift Registry Mode** | 4-5 hours | 🟢 Medium | ⏳ Pending | 📋 [PRD](PRD_WISHLIST_SHARING.md#83-gift-registry-mode-48) - V2 extension of sharing |
| 49 | **Drag-to-Reorder** | 2-3 hours | 🟢 Low | ⏳ Pending | Custom sort order for dashboard |
| 50 | **Secret Santa Mode** | 6-8 hours | 🟢 Medium | ⏳ Pending | 📋 [PRD](PRD_SECRET_SANTA.md) - Random gift assignments for events |


---

## 📊 Progress Summary

**Total Items:** 50
**Completed:** 28 (56%)
**In Progress:** 0 (0%)
**Pending:** 22 (44%)

### By Priority
- 🔴 Critical: 1 pending (Multi-Tenant), 3 complete
- 🟡 High: 4 pending (Privacy, Image Hosting, Share Links ×2), 11 complete
- 🟢 Medium: 8 pending (Variants, A11y, Registry, Secret Santa, etc.), 9 complete
- 🟢 Low: 9 pending, 5 complete

### By Category
- ✅ **Quick Wins:** 6/6 complete (100%)
- ✅ **Infrastructure:** 10/11 complete (91%)
- ✅ **Flask Architecture:** 7/7 complete (100%)
- 🎨 **User Features:** 5/26 complete (19%)

---

## 🎯 Recommended Next Steps

### Ready for Implementation (PRDs Complete)
1. **Item Variants** (#25) - Add size, color, quantity fields. [📋 PRD](PRD_ITEM_VARIANTS.md) ~2 hours
2. **Wishlist Sharing** (#22, #47) - Privacy controls + external share links. [📋 PRD](PRD_WISHLIST_SHARING.md) 6-10 hours
3. **Split Gifts** (#32) - Multiple contributors for expensive items. [📋 PRD](PRD_SPLIT_GIFTS.md) 3-4 hours
4. **Secret Santa Mode** (#50) - Random gift assignments for events. [📋 PRD](PRD_SECRET_SANTA.md) 6-8 hours

### High Priority (No PRD Yet)
5. **Image Hosting** (#44) - Cloudflare R2 for user-uploaded images
6. **Accessibility** (#27) - ARIA labels, keyboard navigation, screen readers

### Future Considerations
7. **Multi-Tenant Support** (#45) - SaaS model for other families (major effort)
8. **Gift Registry Mode** (#48) - Public claiming for weddings/showers
9. **Advanced Search** (#24) - Fuzzy search, price range filters

### New Ideas (Not Yet Tracked)
- **User Profiles** - Allow users to edit name, email, avatar
- **Event Filtering** - Filter items by specific event
- **Calendar View** - Visual calendar for upcoming events
- **Budget Tracking** - Track spending per event or person

---

## 📝 Notes

### Current State
- ✅ 100% test coverage maintained
- ✅ Modern Bootstrap 5 UI
- ✅ Complete surprise protection
- ✅ CSRF protection enabled
- ✅ Database indexes for performance
- ✅ Security headers configured

### Technical Debt
- ~~Email-only authentication (no passwords)~~ ✅ Fixed - Family Code auth implemented (#10)
- No input sanitization - **XSS Risk**
- ~~No rate limiting~~ ✅ Fixed - Flask-Limiter on auth endpoints (#42)
- ~~Monolithic architecture~~ ✅ Fixed - Blueprints implemented (#37-41)
- ~~No containerization~~ ✅ Complete (Docker added)
- ~~No structured logging~~ ✅ Complete (JSON logging added)
- `is_private` field on User model exists but unused (placeholder for #11, #22)

### Infrastructure Needs
- ~~Docker setup~~ ✅ Complete
- ~~Redis for caching~~ ✅ Complete (Ready for use)
- ~~Error tracking (Sentry)~~ ✅ Complete
- Email service (SendGrid/Mailgun) - Currently using Gmail SMTP
- Image storage (Cloudflare R2) - **Next Priority**
- Monitoring solution - Basic Heroku metrics available

---

## 📋 Product Requirements Documents

Detailed PRDs have been created for upcoming features:

| PRD | Related Items | Status | Effort |
|-----|---------------|--------|--------|
| [PRD_ITEM_VARIANTS.md](PRD_ITEM_VARIANTS.md) | #25 (Item Variants) | Draft | ~2 hours |
| [PRD_SPLIT_GIFTS.md](PRD_SPLIT_GIFTS.md) | #32 (Split Gifts) | Draft | 3-4 hours |
| [PRD_WISHLIST_SHARING.md](PRD_WISHLIST_SHARING.md) | #11, #22, #47, #48 (Privacy, Sharing & Registry) | Draft | 6-10 hours |
| [PRD_SECRET_SANTA.md](PRD_SECRET_SANTA.md) | #50 (Secret Santa Mode) | Draft | 6-8 hours |

---

## 🔗 Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Development guide for AI assistants
- [README.md](../README.md) - Project overview and setup
- [pytest.ini](../pytest.ini) - Test configuration
- [.github/workflows/tests.yml](../.github/workflows/tests.yml) - CI/CD pipeline

---

## 📅 Changelog

### 2026-01-03 (Session 6: Project Restructure)
- 🏗️ **Project Restructure**
  - Created `services/` directory with price_service, email_service, tasks, logging_config
  - Moved documentation (DESIGN_UPDATES.md, IMPROVEMENTS.md, GEMINI.md) to `docs/`
  - Moved utility scripts to `scripts/`
  - Updated all imports across app.py and test files
  - Root directory reduced from 42 → 28 items
- 🏗️ **Flask Best Practices Audit**
  - Analyzed app.py against Flask conventions (~65% compliance)
  - Added 6 new improvement items (#37-42) for architecture
  - Identified critical need for blueprints refactoring
  - Updated technical debt and recommended next steps
- ✅ **Blueprint Refactoring (#37, #38)**
  - Split monolithic `app.py` into 6 blueprints: `auth`, `items`, `events`, `dashboard`, `social`, `api`.
  - Implemented Application Factory pattern with `create_app()`.
  - Updated all templates to use blueprint-prefixed `url_for` calls.
  - Verified with full unit test suite (151 tests passed) and browser tests.
- ✅ **Config Integration (#39)**
  - Updated `app.py` to centralized configuration via `config.py`.
  - Added dynamic `DATABASE_URL` handling for Heroku compatibility.
  - Verified Sentry DSN integration.
- ✅ **Global Error Handlers (#40)**
  - Added custom `404`, `500`, and `403` error pages.
  - Implemented automatic database rollback on 500 errors.
  - Added explicit Sentry capture for exceptions.
- ✅ **Extract Models (#41)**
  - Confirmed all 5 models (`User`, `Event`, `Item`, `Comment`, `Notification`) are extracted to `models.py`.
  - Verified `app.py` imports models cleanly.
- ✅ **Rate Limiting on Auth (#42)**
  - Added `Flask-Limiter` dependency.
  - Implemented 5 requests/minute limit on `/login` and `/register`.
  - Configured in-memory storage (with Redis support via env var).
- ✅ **Configure Heroku Redis (#43)**
  - Updated `config.py` to auto-detect Heroku Redis (`REDIS_TLS_URL`, `REDIS_URL`).
  - Verified `Procfile` handles web and release processes.
- ✅ **Proper Authentication (#10)**
  - Implemented shared "Family Code" system (simple, secure shared password).
  - Updated `config.py`, templates, and `auth` blueprint.
  - Verified security with automated tests.
- ✅ All 211 tests passing (151 unit, 60 browser), 96% coverage
- 📈 Progress: 26/43 items complete (60%)

### 2025-10-16 (Session 2)
- ✅ **Docker Containerization (#7)**
  - Created multi-stage Dockerfile for optimized production builds
  - docker-compose.yml with PostgreSQL, Redis, and Flask services
  - Makefile with convenient commands (make up, make test, make logs, etc.)
  - .dockerignore for efficient builds
- ✅ **Environment Config Management (#8)**
  - Added python-dotenv for environment variable management
  - Created config.py with DevelopmentConfig, TestingConfig, ProductionConfig
  - .env.example updated with all configuration options
- ✅ **Logging & Error Tracking (#9)**
  - Structured JSON logging with pythonjsonlogger
  - logging_config.py with customizable formatters
  - Added logging to key routes: register, login, submit_item
  - Development uses human-readable logs, production uses JSON
- 📈 Progress: 9/32 items complete (28%)

### 2025-12-28 (Session 3)
- ✅ **My Claims Page (#33)**
  - New `/my-claims` route showing items claimed/purchased for others
  - Grouped by recipient with status badges
  - Dashboard widget on home page
  - Navbar badge showing claimed items count
- ✅ **Events Management (#34)**
  - Event model with name, date, created_by, reminder_sent fields
  - CRUD routes: /events, /events/new, /events/{id}/edit, /events/{id}/delete
  - Item-event association (optional event_id on items)
  - Events dropdown in submit/edit item forms
- ✅ **Email Notifications (#20)**
  - Flask-Mail integration for sending emails
  - Event reminder emails sent 7 days before events
  - CLI command: `flask send-reminders`
  - HTML and plain text email templates
- ✅ **Price Tracking (#35)**
  - Price fetching service with Amazon support
  - "Refresh Price" button on item cards
  - "Price as of [date]" display
  - CLI command: `flask update-prices`
  - Background price updates for stale items (7+ days)
- ✅ New dependencies: Flask-Mail, beautifulsoup4, requests
- ✅ Database migration: 858a27dc5d01_add_event_model_event_id_and_price_.py
- ✅ Test coverage: 132 tests passing, 94% coverage
- 📈 Progress: 13/35 items complete (37%)

### 2026-01-03 (Session 4)
- ✅ **Fixed Failing Browser Tests**
  - Resolved 9 failing browser tests (100% pass rate restored: 211 tests)
  - Fixed Playwright strict mode violations and timing issues
- 🐛 **Critical Bug Fixes**
  - **Template Rendering:** Fixed `edit_item.html` where `None` values rendered as "None" string, breaking HTML5 validation on URL fields
  - **Login Redirects:** Fixed `next` parameter handling in `login` route and template for proper redirection
- 🧪 **Export Verification Enhancements**
  - Updated export tests to verify actual Excel file content (headers, data) using `pandas`
  - Fixed tests to target correct export endpoints (`/export_items` vs `/export_my_status_updates`)
- 📈 Test coverage: 98% coverage

### 2026-01-03 (Session 5: Docker Infrastructure)
- ✅ **Infrastructure Fixes**
  - **Docker/Colima Setup:** Fixed `lima` Rosetta compatibility issues on Apple Silicon by manual installation of ARM64 binaries.
  - **Dependencies:** Pinned Docker base image to `python:3.11-slim-bookworm` to fix `playwright` dependency failures (missing stable font packages in newer Debian versions).
  - **Permissions:** Refactored Dockerfile to use a virtual environment (`/opt/venv`), resolving `Permission denied` errors for non-root users.
  - **Port Configuration:** Changed default port to **5001** to avoid conflict with macOS AirPlay Receiver (port 5000).
  - **Documentation:** Updated `.gitignore` and `README.md` with streamlined setup instructions.
  - **Redis:** Added Redis service to Docker stack (infrastructure ready for future caching/background tasks).
- ⚙️ **Dev Experience**
  - Auto-generation of `requirements.txt` from `pyproject.toml` for Docker builds.
  - Validated full stack startup (`make up`) including PostgreSQL and Redis.
- ✅ **Error Tracking (Sentry)**
  - Integrated `sentry-sdk` for production error monitoring.
  - Configured environment-based DSN loading.
  - Verified with test exception.
  - **Deployed:** Successfully pushed to Heroku and verified production reporting.

### 2025-10-16 (Session 1)
- ✅ Completed all 6 Quick Wins
- ✅ Added CSRF protection (critical security fix)
- ✅ Added database indexes for performance
- ✅ Added security headers
- ✅ Extracted CSS to static file
- ✅ Created .env.example template
- ✅ Added robots.txt
- ✅ All tests passing (60/60, 100% coverage)
- 📝 Created this IMPROVEMENTS.md tracking document
