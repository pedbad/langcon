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

Common options:
- `--dry-run` to preview changes without writing.
- `--update` to update existing users (password updates only when CSV provides `password`).
- `--send-welcome --site-domain=assess.langcen.cam.ac.uk --use-https` to email login info and reset link.
- `--welcome-message "..."` to append a custom message to the welcome email.
- `--welcome-message-file /path/to/message.txt` to append a file-based message.

Notes:
- `--welcome-message` and `--welcome-message-file` are mutually exclusive.
- `--send-welcome` requires `--site-domain`.

Example commands:
```bash
# Dry run, no changes
python src/manage.py seed_students data/students.csv --dry-run

# Create users with a default password
python src/manage.py seed_students data/students.csv --default-password=ChangeMe123!

# Create users and send welcome emails
python src/manage.py seed_students data/students.csv \
  --send-welcome \
  --site-domain=assess.langcen.cam.ac.uk \
  --use-https

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
  --welcome-message "Welcome to The Adtin  Langusage Condition Assessment.Please complete your profile before starting."
```


---
