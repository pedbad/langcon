# Agents Guide for LangCon
Source repo: https://github.com/pedbad/langcon (forked from https://github.com/pedbad/langcen_base).

Last checked against the code: 2026-10-05. Keep this file as the shared project guide; `CLAUDE.md` imports it for Claude Code.

LangCon supports graduate applicants completing an English-language condition: student onboarding and profiles, a five-step assessment, and staff review. The README also links to the upstream starter; use this repository's implementation as the authority for LangCon behavior.

## 1) Project structure and app organization
- Django project root is `src/`; settings/entrypoints in `src/config` (settings, urls, wsgi/asgi).
- Core reusable UI/utilities in `src/core` (landing/about views, context processors, template tags, shared templates/static).
- Auth and roles in `src/users` (custom email-based user model, role redirects/decorators, auth views, admin, invite utilities, management commands `seed_students` and `send_set_password`; `seed_students` supports `--send-welcome` plus optional `--welcome-message` or `--welcome-message-file`).
- Student profile lifecycle in `src/profiles` (Profile model/validation, forms, signals to auto-create profiles and assessments, student profile page).
- Assessment workflow in `src/assessments` (Assessment/DebateTopic/AssessmentEvaluation models, forms, main assessment view logic, OpenAI LLM services, admin setup).
- Assessor dashboard in `src/assessor` (teacher/admin-facing dashboards and detail view, decision form; includes admin-only student registry view with year filtering/search/sort; depends on assessments).
- Project-level templates also live under `templates/` (cotton components, shared layouts); app templates under each app’s `templates/`.

## 2) Coding patterns and conventions
- Views are mostly function-based with decorators for auth (`login_required`), role gating (`users.decorators.role_required`), and profile completeness (`profiles.utils.require_complete_profile`); class-based views used for Django’s auth flows.
- Register flow is class-based (`users.views.RegisterView`) and role-aware: admin/teacher roles and superusers can access; teacher submissions are forced to `student` role. Other role-decorated views check the explicit role, without a blanket superuser bypass.
- Strict progression in assessment view: action-based POST handler with explicit word-count validation and locking; HTMX-friendly responses for some actions.
- Signals bootstrap related data: create Profile on student creation (feature-flagged), create Assessment when Profile becomes complete, teacher group bootstrap on migrations.
- Admin uses Unfold styling and django-import-export; forms often customized with Unfold widgets for readability.
- Templates rendered via `django-cotton` loader; custom template tags for navigation state, icons, social links, and form attribute injection.
- Styling via Tailwind v4 assets (entrypoint `src/core/static/core/css/input.css`); run `npm run tw:watch` during development or `npm run dev` to build CSS alongside Django. Template directories are explicit (`APP_DIRS=False`, with an explicit app-directories loader).
- UI components follow the shadcn/django patterns provided by `django-cotton` (`templates/cotton/*`); prefer reusing/extending those components for new UI.
- Lint/format: Black and Ruff with line-length 100, target Python 3.13; pytest for tests.

## 3) Key architectural decisions
- Custom `User` model (email as username) with explicit roles (student/teacher/admin); role redirects centralized in settings/utility helpers.
- Profile completeness is the gatekeeper: assessments require a complete Profile; signal ensures Assessment exists once complete.
- Assessment is a single, linear flow per student: writing → LLM Q1 → LLM Q2 → listening → reading. The assessment view assigns a random active DebateTopic when none is attached (including on the first visit), then keeps it stable. A new database needs at least one active topic, created through admin, to make the reading step available; migrations create the topic schema but do not seed topics.
- Listening audio is selected by profile subject-area key from `src/assessments/static/assessments/audio/`. Keep subject keys and filenames aligned. The evaluation service receives a descriptive placeholder for the listening transcript, not the lecture's actual transcript.
- LLM usage is synchronous (OpenAI client from env `OPENAI_API_KEY`) for follow-up question generation and final evaluation (no Celery/queues).
- Admin UX prioritized: Unfold theme, inline AssessmentEvaluation, preview helpers, import/export for users.
- Install Unfold and django-import-export: settings attempt to remove unavailable packages, but app admin modules import them directly, so that fallback does not make them safely optional. Debug mode also requires django-browser-reload and django-extensions.

## 4) Database schema overview
- `users_user`: email-unique auth record with role, is_staff/is_superuser, name fields, date_joined and last_login.
- `profiles_profile`: OneToOne to User; student_number (unique), phone, subject_area, visa flag, honour-code confirmation with timestamp, English exam metadata (type/date/grades/scores with validation/constraints), locking and timestamps. `is_complete()` drives gating.
- `assessments_assessment`: OneToOne to User; writing prompt/answers/timestamps, two LLM follow-up questions and answers, listening prompt/answers, reading answer plus FK to `DebateTopic`, progress/completion helpers, timestamps.
- `assessments_debatetopic`: Debate question with Position A/B text, slug, topic number, active flag; referenced by Assessment.reading_debate (PROTECT).
- `assessments_assessmentevaluation`: OneToOne to Assessment; student email/USN snapshot, submitted_at, completion_duration, LLM evaluation text/model/timestamp/error, assessor recommendation/comment/flags, timestamps and assessor attribution.
- Signals/constraints enforce referential flows; the default database engine is SQLite and environment settings support MySQL via mysqlclient. MySQL-only settings (`OPTIONS.charset`, `TEST.NAME=test_langcon`, test charset/collation) are applied only when `DB_ENGINE` is `django.db.backends.mysql`; keep other backend-specific options conditional the same way. A passing `manage.py check` alone does not verify database connectivity.

## 5) Gotchas and special considerations
- Feature flags: `PROFILES_AUTO_CREATE` can disable auto profile creation; `TEACHER_ADMIN_FULL_PERMS` controls teacher group permissions (view-only vs full). Both are currently hard-coded to `True` in settings, not read from environment variables.
- `OPENAI_API_KEY` is required for live follow-up generation and evaluation, not for ordinary page rendering or mocked tests. Calls are synchronous inside views.
- Server-side word limits in `src/assessments/views.py`: initial writing 300–350; follow-up Q1 200–250; follow-up Q2 100–150; listening 250–350; reading 250–300. Drafts are truncated to 3000 characters. Some comments/docstrings still show older limits; use the actual validation branches and keep templates consistent when changing them.
- `Assessment.is_complete()` is a legacy method excluding reading; `Assessment.is_fully_complete` is the property covering all five steps. Final evaluation is created after reading submission when fully complete.
- LLM service wrappers live in `src/assessments/services/`, with prompt/vendor code in `src/assessments/vendor/`; question generation and evaluation currently default to `gpt-4o-mini`. Mock these boundaries in tests instead of making live API calls.
- Writing is saved and locked before follow-up generation. If generation fails, the view displays a warning but has no background job or refresh-triggered retry. Evaluation likewise creates its record before the API call; existing records skip generation. Preserve submitted answers when working on failure recovery. Client initialization in the evaluation service is outside its exception handler.
- Assessment flow is gated: Q2 requires Q1 final; listening requires Q2 final; reading requires listening final and assigned debate; once final fields set they’re locked.
- Profile validation is strict when exams are reported (date within 5 years, score ranges/steps, Cambridge-specific fields); honour code must be checked. `student_number` is unique, may be null for a new profile, and accepts letters, digits and hyphens up to 20 characters; completion requires it.
- Student profile editing becomes read-only when `is_locked` or `is_complete()` is true. Separately, `is_complete()` returns false for an explicitly locked profile, so setting `is_locked=True` also blocks assessment access through the completeness gate.
- Dev email backend writes to `tmp_emails/` unless overridden; production expects SMTP env vars.
- The post-migrate bootstrap syncs existing teachers to staff and the `Teacher Admin` group. Web registration sets staff/group membership for new teachers; assigning a teacher role directly through the model does not itself do this. With `TEACHER_ADMIN_FULL_PERMS=True`, the group receives all permissions, not just assessment permissions.
- Creating a non-superuser without a usable password schedules an invite email after transaction commit. This can happen independently of `seed_students --send-welcome`, which controls its separate welcome email. Use the development file backend or a test mail backend for local work.
- Tests run with pytest-django (`pytest.ini` sets `DJANGO_SETTINGS_MODULE=config.settings` and `pythonpath=src`).
- Test fixtures should reuse the profile created by the user signal (`get_or_create` or update `user.profile`), or explicitly disable `PROFILES_AUTO_CREATE` when testing manual creation. The current `test_register_rejects_duplicate_student_number` fixture creates a second profile for the same user and fails on the user/profile unique constraint before reaching its intended assertion.
- Production URL mounting is controlled by `FORCE_SCRIPT_NAME`, defaulting to `/langcon` when `ENV=prod`; local development defaults to the root path. Email backend selection uses `ENV`, while development tools use `DEBUG`.

## 6) Local setup and verification
- Run commands from the repository root. `.python-version` pins 3.13.3; formatting targets Python 3.13. Reuse an existing virtual environment, or create one with `python3.13 -m venv .venv`, then `source .venv/bin/activate`.
- Install Python development dependencies with `python -m pip install -r requirements-dev.txt`, and frontend dependencies with `npm install`. The Python requirements include mysqlclient even when planning to use SQLite; building it from source requires native MySQL client build dependencies.
- For a new checkout, copy `.env.example` to `.env` only if `.env` does not already exist. Settings load this root file. Set database connection values for your local database, or leave the `DB_*` values unset to use SQLite. Replace or remove the example `EMAIL_FILE_PATH=/absolute/path/to/tmp_emails` so development email uses a valid directory.
- Once the local database is configured: `python src/manage.py migrate`, optionally `python src/manage.py createsuperuser`, then `npm run dev` (Django plus Tailwind watcher). Add an active DebateTopic in `/admin/` before testing the full student journey.
- Django checks: `python src/manage.py check`. Tests: `python -m pytest`, or a targeted path such as `python -m pytest src/users/tests/test_register.py`. Tests use `config.settings`, including its database configuration; use a local/test database configuration.
- For Python changes, check affected files with `python -m black --check <paths>` and `python -m ruff check --no-fix <paths>`; Ruff otherwise defaults to auto-fixing in this repo.
- After template/style changes, build CSS with `npm run tw:build`; output is `src/core/static/core/css/output.css` (gitignored). For model changes, create migrations with `python src/manage.py makemigrations` and check with `python src/manage.py makemigrations --check --dry-run`.
- Student import instructions and CSV options are in `SEED_STUDENTS_GUIDE.md` and `README.md`. Use `--dry-run` to preview imports.
- Keep real `.env` credentials, student data, database files, and generated invitation emails out of commits and tool output.
