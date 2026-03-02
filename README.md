# langcon - Graduate Applications - Language Condition

![Python](https://img.shields.io/badge/python-3.13-blue)
![Django](https://img.shields.io/badge/django-5.2-green)
![Tailwind](https://img.shields.io/badge/tailwind-4.1-blueviolet)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version](https://img.shields.io/badge/version-v0.1.0--ui--refresh-orange)


---

For full documentation, see the repo at [github.com/pedbad/langcen_base](https://github.com/pedbad/langcen_base).

## Management commands

### Seed students (CSV)

Command:
```bash
python src/manage.py seed_students /path/to/students.csv
```

Required CSV columns:
- `email`
- `first_name`
- `last_name`
- `student_number` (USN / ADTIS identifier)

Optional CSV column:
- `password`

Common options:
- `--dry-run` to preview changes without writing.
- `--update` to update existing users (password updates only when CSV provides `password`).
- `--send-welcome --site-domain=assess.langcen.cam.ac.uk --use-https` to email login info and reset link.
- `--welcome-message "..."` to append a custom message to the welcome email.
- `--welcome-message-file /path/to/message.txt` to append a file-based message.

Notes:
- `--welcome-message` and `--welcome-message-file` are mutually exclusive.
- `--send-welcome` requires `--site-domain`.
- `student_number` is validated and must be unique.

Example commands:
```bash
# Dry run, no changes
python src/manage.py seed_students data/students.csv --dry-run

# Preview welcome emails (dry-run)
python src/manage.py seed_students data/students.csv --dry-run \
  --send-welcome \
  --site-domain=assess.langcen.cam.ac.uk \
  --use-https \
  --welcome-message-file data/message.txt

# Create users with a default password
python src/manage.py seed_students data/students.csv --default-password=ChangeMe123!

# Create users and send welcome emails
python src/manage.py seed_students data/students.csv \
  --send-welcome \
  --site-domain=assess.langcen.cam.ac.uk \
  --use-https

# Send welcome emails for real (with a file-based custom message)
python src/manage.py seed_students data/students.csv \
  --send-welcome \
  --site-domain=assess.langcen.cam.ac.uk \
  --use-https \
  --welcome-message-file data/message.txt

# Update existing users and email only when CSV includes a password
python src/manage.py seed_students data/students.csv \
  --update \
  --send-welcome \
  --site-domain=assess.langcen.cam.ac.uk \
  --use-https

# Send a custom welcome message
python src/manage.py seed_students data/students.csv \
  --send-welcome \
  --site-domain=assess.langcen.cam.ac.uk \
  --use-https \
  --welcome-message "Welcome to LangCon! Please complete your profile before starting."

# Send a custom welcome message from a file
python src/manage.py seed_students data/students.csv \
  --send-welcome \
  --site-domain=assess.langcen.cam.ac.uk \
  --use-https \
  --welcome-message-file data/message.txt
```

Detailed walkthrough for non-technical operators:
- See [`SEED_STUDENTS_GUIDE.md`](SEED_STUDENTS_GUIDE.md)

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
