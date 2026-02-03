# Agents Guide for LangCon
Source repo: https://github.com/pedbad/langcon (forked from https://github.com/pedbad/langcen_base).

## 1) Project structure and app organization
- Django project root is `src/`; settings/entrypoints in `src/config` (settings, urls, wsgi/asgi).
- Core reusable UI/utilities in `core` (landing/about views, context processors, template tags, shared templates/static).
- Auth and roles in `users` (custom email-based user model, role redirects/decorators, auth views, admin, invite utilities, management commands `seed_students` and `send_set_password`; `seed_students` supports `--send-welcome` plus optional `--welcome-message` or `--welcome-message-file`).
- Student profile lifecycle in `profiles` (Profile model/validation, forms, signals to auto-create profiles and assessments, student profile page).
- Assessment workflow in `assessments` (Assessment/DebateTopic/AssessmentEvaluation models, forms, main assessment view logic, OpenAI LLM services, admin setup).
- Assessor dashboard in `assessor` (teacher/admin-facing dashboards and detail view, decision form; depends on assessments).
- Project-level templates also live under `templates/` (cotton components, shared layouts); app templates under each app’s `templates/`.

## 2) Coding patterns and conventions
- Views are mostly function-based with decorators for auth (`login_required`), role gating (`users.decorators.role_required`), and profile completeness (`profiles.utils.require_complete_profile`); class-based views used for Django’s auth flows.
- Strict progression in assessment view: action-based POST handler with explicit word-count validation and locking; HTMX-friendly responses for some actions.
- Signals bootstrap related data: create Profile on student creation (feature-flagged), create Assessment when Profile becomes complete, teacher group bootstrap on migrations.
- Admin uses Unfold styling and django-import-export; forms often customized with Unfold widgets for readability.
- Templates rendered via `django-cotton` loader; custom template tags for navigation state, icons, social links, and form attribute injection.
- Styling via Tailwind v4 assets (entrypoint `core/static/core/css/input.css`); run `npm run tw:watch` during development or `npm run dev` to build CSS alongside Django. Template directories are explicit (no `APP_DIRS`).
- UI components follow the shadcn/django patterns provided by `django-cotton` (`templates/cotton/*`); prefer reusing/extending those components for new UI.
- Lint/format: Black and Ruff with line-length 100, target Python 3.13; pytest for tests.

## 3) Key architectural decisions
- Custom `User` model (email as username) with explicit roles (student/teacher/admin); role redirects centralized in settings/utility helpers.
- Profile completeness is the gatekeeper: assessments require a complete Profile; signal ensures Assessment exists once complete.
- Assessment is a single, linear flow per student: writing → LLM Q1/Q2 → listening → reading; reading assigns a random active DebateTopic once per Assessment.
- LLM usage is synchronous (OpenAI client from env `OPENAI_API_KEY`) for follow-up question generation and final evaluation (no Celery/queues).
- Admin UX prioritized: Unfold theme, inline AssessmentEvaluation, preview helpers, import/export for users.
- Optional third-party toggles: Unfold and import-export removed if not importable; dev tools only added in DEBUG.

## 4) Database schema overview
- `users_user`: email-unique auth record with role, is_staff/is_superuser, name fields, timestamps.
- `profiles_profile`: OneToOne to User; student_number (unique), phone, subject_area, visa flag, honour-code confirmation with timestamp, English exam metadata (type/date/grades/scores with validation/constraints), locking and timestamps. `is_complete()` drives gating.
- `assessments_assessment`: OneToOne to User; writing prompt/answers/timestamps, two LLM follow-up questions and answers, listening prompt/answers, reading answer plus FK to `DebateTopic`, progress/completion helpers, timestamps.
- `assessments_debatetopic`: Debate question with Position A/B text, slug, topic number, active flag; referenced by Assessment.reading_debate (PROTECT).
- `assessments_assessmentevaluation`: OneToOne to Assessment; student email/USN snapshot, submitted_at, completion_duration, LLM evaluation text/model/timestamp/error, assessor recommendation/comment/flags, timestamps and assessor attribution.
- Signals/constraints enforce referential flows; SQLite by default, env-driven DB settings support MySQL via mysqlclient.

## 5) Gotchas and special considerations
- Feature flags: `PROFILES_AUTO_CREATE` can disable auto profile creation; `TEACHER_ADMIN_FULL_PERMS` controls teacher group permissions (view-only vs full).
- OpenAI dependence: `OPENAI_API_KEY` required; calls are synchronous inside views (can block requests; handle exceptions gracefully but still part of request cycle).
- Word limits enforced server-side (250–300 words) for writing/follow-up/listening/reading; drafts are truncated to 3000 chars.
- Assessment flow is gated: Q2 requires Q1 final; listening requires Q2 final; reading requires listening final and assigned debate; once final fields set they’re locked.
- Profile validation is strict when exams are reported (date within 5 years, score ranges/steps, Cambridge-specific fields); honour code must be checked; `student_number` unique.
- Template loading uses cotton loader and explicit DIRS with `APP_DIRS=False`; ensure cotton components exist or adjust loaders for production cached loader.
- Dev email backend writes to `tmp_emails/` unless overridden; production expects SMTP env vars.
- Teacher group/bootstrap runs on every migrate; teachers become staff automatically. Creating users without passwords triggers invite email on post-save.
- Admin URLs rely on Unfold/Import-Export; if those packages missing, settings strip them from INSTALLED_APPS.
- Tests run with pytest-django (`pytest.ini` sets `DJANGO_SETTINGS_MODULE=config.settings` and `pythonpath=src`).
- Frontend build dependency: Tailwind output must be rebuilt via npm scripts; keep a watcher running or CSS changes won’t appear.
- UI consistency: lean on the cotton/shadcn component set in `templates/cotton` before introducing new patterns.
