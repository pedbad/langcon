# LangCon — Graduate Applications · Language Condition

![Python](https://img.shields.io/badge/python-3.13-blue)
![Django](https://img.shields.io/badge/django-5.2-green)
![Tailwind](https://img.shields.io/badge/tailwind-4.1-blueviolet)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

LangCon manages English-language assessments for graduate applicants: staff create student accounts, students complete their profiles and assessment, and assessors review the results and record a recommendation.

**Repository:** [pedbad/langcon](https://github.com/pedbad/langcon), on `main`. It was forked from [pedbad/langcen_base](https://github.com/pedbad/langcen_base). The upstream repository is background for the starter; this README describes the application in this repository.

The application details below were checked against the source on **5 October 2026**. Use the dependency files for package versions and the deployed Git commit to identify the application revision.

## Contents

- [How the application works](#how-the-application-works)
- [Technology and directory structure](#technology-and-directory-structure)
- [Local development](#local-development)
- [Configuration to remember](#configuration-to-remember)
- [Where to make changes](#where-to-make-changes)
- [Checks and maintenance](#checks-and-maintenance)
- [Management commands](#management-commands)
- [Returning to the deployment](#returning-to-the-deployment)

## How the application works

1. **Create accounts.** Admins and teachers can register students; teachers can only create student accounts. CSV import supports bulk onboarding. Users sign in with their email address.
2. **Complete a profile.** A student needs a phone number, student number, subject area and honour-code confirmation, plus the required exam details if reporting a recent English exam. A signal normally creates the profile when the student is created, and creates an assessment when the profile becomes complete.
3. **Complete five assessment steps.** Each step must be submitted before the next becomes available. Students can save drafts; final answers are locked against further student edits.
4. **Review the result.** The final reading submission creates an evaluation record and calls OpenAI for an evaluation. Teachers/admins use the assessor dashboard to record their recommendation, comment, marking status, phone follow-up and archive flags.

| Step | Task | Accepted word count |
| --- | --- | --- |
| 1 | Initial writing about postgraduate research or programme choice | 300–350 |
| 2 | First AI-generated follow-up question | 200–250 |
| 3 | Second AI-generated follow-up question | 100–150 |
| 4 | Summary of a subject-related listening passage | 250–350 |
| 5 | Reading response to a debate topic | 250–300 |

These limits are enforced in [the assessment view](src/assessments/views.py), not just in the browser. Stored drafts are limited to 3,000 characters. Some source comments still show older word limits; check the actual validation branches when changing them.

**Content and data relationships:** each student has at most one Profile and one Assessment; each Assessment has at most one AssessmentEvaluation. Reading uses a shared DebateTopic record, assigned randomly from active topics when an assessment without a topic is opened. The assignment is kept stable, and referenced topics are protected against deletion. Topics live in the database; migrations do not seed them. Listening MP3s are stored in the repository and selected by the profile's subject-area key.

The topic reference is stable, but its text is not copied into each assessment. Editing an existing topic changes the material displayed by assessments linked to it. Create a new topic for revised material if the older text must remain available.

**Completion has two meanings in the code:** `Assessment.is_complete()` is a legacy method that excludes reading. `Assessment.is_fully_complete` includes all five steps. Recorded completion duration runs from initial writing submission to final reading submission, not from first login or the start of drafting. Evaluation email/USN fields are snapshots taken at submission.

**Profile locking:** students cannot edit a profile that is complete or explicitly locked. Setting `Profile.is_locked=True` also makes `is_complete()` false and blocks assessment access; it is not simply an “already completed” marker.

## Technology and directory structure

This is a server-rendered Django application, with django-cotton components, Tailwind CSS, and HTMX/Alpine.js for browser interactions. Node/npm builds CSS and runs development scripts; it is not the application server. Django Unfold styles the admin and django-import-export handles admin imports/exports. OpenAI calls are synchronous; there is no background worker or job queue.

```text
langcon/
├── src/
│   ├── manage.py                 # Django command entry point
│   ├── config/                   # Settings, root URLs, WSGI/ASGI entry points
│   ├── core/                     # Landing/about pages, shared UI and template tags
│   │   ├── templates/core/       # Base layout, page partials, icons
│   │   └── static/core/          # CSS source, JavaScript, images
│   ├── users/                    # Email login, roles, registration, invitations
│   │   └── management/commands/  # seed_students and send_set_password
│   ├── profiles/                 # Student details, exam validation, completion gate
│   ├── assessments/              # Five-step flow, questions, answers, evaluation
│   │   ├── services/             # OpenAI service wrappers and evaluation inputs
│   │   ├── vendor/               # Question/evaluation prompt implementations
│   │   ├── templates/            # Assessment page and step cards
│   │   └── static/assessments/audio/  # Subject-specific listening MP3s
│   └── assessor/                 # Staff dashboard, student registry, review form
├── templates/cotton/             # Reusable UI components
├── data/                         # CSV input location; sample_students.csv is tracked
├── .env.example                  # Configuration template; actual .env is untracked
├── .python-version               # Python 3.13.3
├── requirements.txt              # Direct runtime dependencies
├── requirements-dev.txt          # Runtime plus development/test tools
├── requirements-full.txt         # Fully pinned dependency snapshot
├── package.json                  # Tailwind and development npm scripts
├── pyproject.toml                # Black/Ruff configuration
├── pytest.ini                    # Django test settings and src import path
├── SEED_STUDENTS_GUIDE.md         # Detailed operator guide for student imports
├── AGENTS.md                     # Shared coding-agent project instructions
└── CLAUDE.md                     # Imports AGENTS.md for Claude Code
```

Models and database migrations belong to their respective apps. App-specific templates live under each app's `templates/`; the shared base layout is [src/core/templates/core/base.html](src/core/templates/core/base.html). Template loaders are configured explicitly in settings, with the cotton loader first and `APP_DIRS=False`.

Generated/local directories include `.venv/`, `node_modules/`, `tmp_emails/`, and `src/staticfiles/` (the `collectstatic` destination). Tailwind generates `src/core/static/core/css/output.css`; that file is gitignored and must be rebuilt after checkout. The database and real student CSVs are not supplied by cloning the repository.

## Local development

Run commands from the repository root. The project targets Python 3.13; `.python-version` pins 3.13.3. Use Node.js/npm for the frontend build; the repository does not pin a Node version or track an npm lockfile.

```bash
# For a new checkout; reuse an existing virtual environment if present.
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
npm install
```

`mysqlclient` is included even if you intend to use SQLite; building it from source needs native MySQL client build dependencies. Install the development requirements for `DEBUG=True`, because browser reload and Django extensions are enabled in that mode. Unfold/import-export are also required by direct imports in admin modules despite the optional-package fallback in settings.

Copy `.env.example` to `.env` **only for a fresh setup with no existing `.env`**. Review its placeholders, especially `SECRET_KEY`, database settings, `OPENAI_API_KEY`, and `EMAIL_FILE_PATH`. Remove the example `/absolute/path/to/tmp_emails` override to use the repository's default mail folder, or replace it with a valid path.

### Choose and configure the database first

[Settings](src/config/settings.py) accept MySQL through `DB_ENGINE=django.db.backends.mysql` and `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`. Create a local database/account and configure those values before migrating.

**Database backends:** SQLite is the default engine when `DB_ENGINE` is unset. MySQL-only settings (`OPTIONS.charset`, the fixed `test_langcon` test database name, and test charset/collation) are applied only when `DB_ENGINE=django.db.backends.mysql`. A successful `manage.py check` alone does not prove the database connection works.

Once the local database is configured:

```bash
python src/manage.py check
python src/manage.py migrate
python src/manage.py createsuperuser
npm run dev
```

`npm run dev` runs Django's development server and the Tailwind watcher together. Open `http://127.0.0.1:8000/`. Before testing the complete student journey, use `/admin/` to create at least one **active DebateTopic**, then create a student through registration or CSV import. A real OpenAI key is needed to generate follow-up questions and the final evaluation.

| Local path | Purpose |
| --- | --- |
| `/users/login/` | Email/password login |
| `/users/register/` | Staff account creation |
| `/users/student/` | Student dashboard |
| `/users/profile/` | Student profile |
| `/users/assessments/home/` | Assessment, gated by profile completion |
| `/assessor/` | Teacher/admin review dashboard |
| `/assessor/students/` | Admin-only student registry, including incomplete profiles |
| `/admin/` | Django admin for users, profiles, topics and assessments |

These paths acquire the configured prefix when the application is mounted under a subpath.

## Configuration to remember

The root `.env` is loaded by [src/config/settings.py](src/config/settings.py). Existing process environment variables take precedence. Keep credentials and student data out of Git.

| Setting | What it controls |
| --- | --- |
| `ENV` | Defaults to `dev`; selects file email in development versus SMTP otherwise. `ENV=prod` also defaults the URL prefix to `/langcon`. |
| `DEBUG` | Defaults to true independently of `ENV`; enables Django debug tools. Set explicitly for deployment. |
| `SECRET_KEY`, `ALLOWED_HOSTS` | Django secret and allowed hostnames. |
| `SITE_NAME`, `SITE_DESCRIPTION`, `SITE_ORIGIN` | Site identity/metadata; the origin includes the scheme. |
| `SITE_DOMAIN` | Hostname, optionally port, used for invitation links without a request. Do not include a scheme or path. |
| `FORCE_SCRIPT_NAME` | URL prefix: empty locally, `/langcon` by default with `ENV=prod`. Set explicitly to match the reverse proxy. |
| `DB_*` | Database connection settings. `DB_CHARSET`/`DB_COLLATION` apply to MySQL only. See the database note above. |
| `OPENAI_API_KEY` | Used by question generation and evaluation; unnecessary for ordinary page rendering or mocked tests. |
| `EMAIL_BACKEND`, `EMAIL_FILE_PATH` | Override email delivery and development outbox location. Default development outbox is `tmp_emails/`. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | SMTP settings read outside `ENV=dev`. |
| `DEFAULT_FROM_EMAIL`, `SERVER_EMAIL` | Sender addresses. |

`SITE_USE_HTTPS` appears in `.env.example` but is **not read by the current application**. The automatic account-creation invitation uses HTTP; command-generated messages use their explicit HTTPS flags described below. Changing that unused environment variable will not fix invitation links.

`PROFILES_AUTO_CREATE` and `TEACHER_ADMIN_FULL_PERMS` are Python settings currently set to `True`, not environment switches. On migration, the teacher bootstrap grants the `Teacher Admin` group all permissions when full permissions are enabled and syncs existing teachers to staff/group membership. Web registration sets membership for new teachers; merely assigning `role="teacher"` through the model does not. Business roles and Django's staff/superuser flags serve different purposes.

## Where to make changes

| Change | Start here |
| --- | --- |
| Assessment progression, word limits, submission locking | [assessments/views.py](src/assessments/views.py), [forms.py](src/assessments/forms.py), and [step templates](src/assessments/templates/assessments/partials/) |
| Writing/listening prompt defaults and stored data | [assessments/models.py](src/assessments/models.py); model changes may need migrations and existing records may need separate updates |
| AI questions or evaluation wording/model | [services/](src/assessments/services/) and [vendor/](src/assessments/vendor/); both service defaults currently use `gpt-4o-mini` |
| Reading material | DebateTopic records in Django admin; existing assessments retain their assigned topic reference |
| Listening material | [audio files](src/assessments/static/assessments/audio/) and [listening template](src/assessments/templates/assessments/partials/listening_card.html); filenames match profile subject keys |
| Profile requirements, exam scores and validation | [profiles/models.py](src/profiles/models.py), [forms.py](src/profiles/forms.py), [views.py](src/profiles/views.py) |
| Staff decisions and dashboard filters | [assessor/views.py](src/assessor/views.py), [forms.py](src/assessor/forms.py), and AssessmentEvaluation in [assessment models](src/assessments/models.py) |
| Layout, navigation, appearance | [shared templates](src/core/templates/core/), [cotton components](templates/cotton/), [input.css](src/core/static/core/css/input.css) |
| Email content and links | [users/utils.py](src/users/utils.py), [email templates](src/users/templates/users/registration/), and [seed_students.py](src/users/management/commands/seed_students.py) for its separate welcome message |
| Site settings and route mounting | [config/settings.py](src/config/settings.py) and [config/urls.py](src/config/urls.py) |

AI evaluation currently receives a descriptive placeholder for the listening transcript, **not the actual lecture transcript**. For reading it receives the assigned topic's question and positions. Consider this limitation when interpreting or changing the evaluation.

Submitted writing is saved before follow-up generation. A failed generation can leave writing locked without questions; the warning suggests refreshing, but there is no refresh-triggered retry or background job. The final evaluation record is likewise created before its API call; some failures populate `llm_error`, and client initialization occurs outside the service's exception handler. There is no general retry command in the repository. Inspect the stored answers/questions/evaluation before attempting recovery, preserving submitted work.

## Checks and maintenance

Activate the virtual environment and use a local/test database configuration. Pytest uses `config.settings`; there is no separate test settings module. MySQL tests use the configured fixed name `test_langcon`, so the test account needs appropriate permissions on a separate test database.

```bash
python src/manage.py check
python -m pytest
# A smaller test selection:
python -m pytest src/users/tests/test_register.py src/assessments/tests/test_assessment_access.py

# Build CSS after template/style changes:
npm run tw:build

# Check only the Python files you changed (replace the example path):
python -m black --check src/users/views.py
python -m ruff check --no-fix src/users/views.py

# After model changes, generate and review migrations:
python src/manage.py makemigrations
python src/manage.py makemigrations --check --dry-run
python src/manage.py migrate
```

Black/Ruff use a 100-character line length and Python 3.13 target. Ruff defaults to fixing files in this repo, hence `--no-fix` for a read-only check. Pre-commit hooks are configured in [.pre-commit-config.yaml](.pre-commit-config.yaml).

**Known test baseline (5 October 2026):** the targeted selection above produced seven passes and one failure using temporary in-memory SQLite settings with the incompatible database options removed. `test_register_rejects_duplicate_student_number` creates a profile that the user signal already created, failing before its intended assertion. This is not a passing full-suite baseline or a claim that the default SQLite configuration works.

For static assets, build Tailwind **before** `python src/manage.py collectstatic --noinput`; Django collects into `src/staticfiles/` for the production web server to serve. `STATIC_VERSION` in settings is a manual cache-busting value used by shared templates. Browser-side libraries include local HTMX/Alpine copies; the shared scripts template also loads an external CIVIC cookie-control script.

The direct dependency files are the installation entry points. `requirements-full.txt` is a pinned snapshot, while `requirements.txt` permits Django 5.2 patch updates and npm dependencies use version ranges. Do not assume a fresh install years later reproduces today's environment exactly. Record a known-working Git commit and deployed dependency versions when maintaining the server.

## Management commands

### Seed students (CSV)

Detailed operator instructions: [SEED_STUDENTS_GUIDE.md](SEED_STUDENTS_GUIDE.md). Source of current behavior: [seed_students.py](src/users/management/commands/seed_students.py).

Required columns are `email`, `first_name`, `last_name`, `student_number`; all need nonempty values. `password` is optional. Student numbers must be unique and contain only letters, digits or hyphens, up to 20 characters. The importer trims values and lowercases email addresses. Invalid/duplicate rows are reported and skipped; inspect the final counts rather than assuming every row was imported.

| Option | Behavior |
| --- | --- |
| `--dry-run` | Reports proposed creates/updates and, with `--send-welcome`, intended recipients. It does not render a preview email body. See the edge case below. |
| `--update` | Updates matching students' names and student number; changes passwords only when a nonempty CSV password is supplied. Existing users are otherwise skipped; non-students are skipped on update. |
| `--default-password` | Fallback password for new accounts only; ignored on updates. Without a CSV/default password, new accounts receive an unusable password. |
| `--send-welcome` | Sends the separate welcome message for new users and updates with a supplied password. Requires `--site-domain`. The email includes any temporary password supplied. |
| `--site-domain`, `--use-https` | Hostname/port and HTTPS choice for welcome links. Without the flag, links use HTTP. |
| `--welcome-message`, `--welcome-message-file` | Append text to the welcome email; mutually exclusive. |
| `--from-email` | Override the welcome email sender. |

```bash
# Preview a new student import:
python src/manage.py seed_students data/students.csv --dry-run

# Report intended welcome-email recipients as well:
python src/manage.py seed_students data/students.csv --dry-run \
  --send-welcome --site-domain=assess.langcen.cam.ac.uk --use-https \
  --welcome-message-file data/message.txt

# Real import and welcome messages:
python src/manage.py seed_students data/students.csv \
  --send-welcome --site-domain=assess.langcen.cam.ac.uk --use-https \
  --welcome-message-file data/message.txt

# Update existing students; welcome messages go to updates with a CSV password:
python src/manage.py seed_students data/students.csv --update \
  --send-welcome --site-domain=assess.langcen.cam.ac.uk --use-https
```

The hostname above is retained from the existing operator examples; replace it with the actual deployment hostname. `data/students.csv` and `data/message.txt` are operator-provided inputs, not prerequisites supplied by this README. Real CSVs under `data/` are gitignored apart from the tracked sample; message text files are not covered by that CSV rule.

**Two email paths exist.** Creating a non-superuser with an unusable password triggers a separate set-password invitation through `users/signals.py`, even without `--send-welcome`. Combining that creation with `--send-welcome` can send two messages. The automatic invitation takes its domain from `SITE_DOMAIN` and uses HTTP; the welcome command uses `--site-domain` and `--use-https`. Confirm the development file outbox or intended SMTP configuration before an import.

**Dry-run edge case:** `--update --dry-run` calls `Profile.objects.get_or_create()` for an existing student before checking the dry-run branch. If that student has no profile, it creates one. This was reproduced with synthetic data in an isolated database. Do not treat that path as strictly read-only. Imports are also not wrapped in one all-or-nothing transaction, so an interrupted import may leave earlier rows applied.

### Send or resend a set-password email

For an existing active user, including one with an unusable password:

```bash
# Local development: inspect tmp_emails/ with the default file backend.
python src/manage.py send_set_password student@example.com --domain=127.0.0.1:8000

# Deployment: replace the sample address and hostname.
python src/manage.py send_set_password student@example.com \
  --domain=assess.langcen.cam.ac.uk --https
```

This command uses `--domain` and `--https`, unlike the CSV command's `--site-domain` and `--use-https`. It also accepts `--from-email`. Without `--domain` it uses `SITE_DOMAIN`; provide `--https` explicitly for HTTPS links. Reset tokens expire after 24 hours under the current settings. Source: [send_set_password.py](src/users/management/commands/send_set_password.py).

## Returning to the deployment

The repository describes application configuration, but it does not contain the server's `~/scripts` helpers, reverse-proxy configuration, service definitions or a complete deployment runbook. The server notes below are retained from the existing README; their current contents/existence have not been verified from this checkout.

For a future handover, record the actual server/SSH alias, checkout and virtualenv paths, service name and restart/log commands, public URL/prefix, database backup/restore location and procedure, and where deployment secrets are managed. Keep secrets themselves outside this README. Back up the database: accounts, profiles, answers, reading topics and staff decisions cannot be recovered from Git. A cloned repo and migrations recreate the schema, not the live records.

### Deployment helper scripts (server)

On the deployment server, there are helper scripts under `~/scripts`:

- `addusers-and-send-email.sh` — runs a real send using the configured CSV and message file.
- `dryrun-addusers-and-send-email.sh.org` — runs a dry run (no database changes).

Run them like this (as the `administrator` user):
```bash
cd ~/scripts
bash addusers-and-send-email.sh
bash dryrun-addusers-and-send-email.sh.org
```


---
