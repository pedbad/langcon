# Student Seeding Guide (Webmaster-Friendly)

This guide explains how to add many student accounts in bulk using a CSV file.

It is written for non-technical operators and can be followed step by step.

## 1) What this tool does

`seed_students` reads a CSV and creates or updates student users.

It can also send welcome emails with password-reset links.

## 2) Where to run commands

Run all commands from the project root:

```bash
cd /path/to/langcon
```

If this project uses a local Python environment, activate it first:

```bash
source .venv/bin/activate
```

## 3) CSV format (required)

Your CSV **must** include these columns exactly:

- `email`
- `first_name`
- `last_name`
- `student_number`

Optional column:

- `password`

Notes:

- `student_number` is the USN or ADTIS identifier.
- `student_number` must be unique.
- If `password` is empty, you can provide a default password with `--default-password`.
- If both CSV `password` and `--default-password` are present, CSV password wins.

## 4) Example CSV

You can test immediately with:

- [`data/sample_students.csv`](data/sample_students.csv)

Example format:

```csv
email,first_name,last_name,student_number,password
alice@example.com,Alice,Anderson,300000001,
bob@example.com,Bob,Barnes,300000002,
charlie@example.com,Charlie,Chaplin,300000003,TempPass!123
```

## 5) Safest workflow (recommended)

Always do this in order:

1. Run a dry run.
2. Check output carefully.
3. Run the real import.
4. Optionally send welcome emails.

## 6) Dry run (no changes made)

```bash
python src/manage.py seed_students data/sample_students.csv --dry-run --default-password=ChangeMe123!
```

What to look for:

- `would create: ...` means account would be created.
- `would update: ...` means existing account would be updated (only when `--update` is used).
- `... -> skip` means row was ignored (invalid or not applicable).
- Summary line shows totals.

## 7) Real create run

```bash
python src/manage.py seed_students data/sample_students.csv --default-password=ChangeMe123!
```

What this does:

- Creates student users that do not exist yet.
- Sets first name, last name, and student number.
- Uses CSV password if present, otherwise `--default-password`.
- If no password is available, account is created with unusable password.

## 8) Update existing students

Use this when records already exist and you want to correct names/USN or set a new password from CSV.

```bash
python src/manage.py seed_students data/sample_students.csv --update
```

Important:

- In update mode, password changes only if that row has a `password` value.
- `--default-password` is ignored for existing users in update mode.

## 9) Send welcome emails

To send welcome emails during create/update:

```bash
python src/manage.py seed_students data/sample_students.csv \
  --default-password=ChangeMe123! \
  --send-welcome \
  --site-domain=assess.langcen.cam.ac.uk \
  --use-https
```

Email options:

- `--site-domain` is required when using `--send-welcome`.
- `--use-https` uses `https://` in links.
- `--from-email=...` sets sender.
- `--welcome-message "..."` appends a custom message.
- `--welcome-message-file data/message.txt` appends content from a file.
- `--welcome-message` and `--welcome-message-file` cannot be used together.

## 10) Preview emails without sending (recommended first)

```bash
python src/manage.py seed_students data/sample_students.csv \
  --dry-run \
  --send-welcome \
  --site-domain=assess.langcen.cam.ac.uk \
  --use-https \
  --welcome-message-file data/message.txt
```

This previews email activity while making no database changes.

## 11) Typical errors and fixes

- `CSV must include required column(s): ...`
  - Your header is missing one or more required columns.
- `invalid email ... -> skip`
  - Fix the email in CSV.
- `invalid student_number ... -> skip`
  - Student number format is invalid.
- `student_number '...' already used ... -> skip`
  - USN/ADTIS must be unique.
- `--site-domain is required when using --send-welcome`
  - Add `--site-domain=...`.

## 12) Good operating practices

- Keep one source CSV per batch and archive it.
- Always run `--dry-run` before real run.
- Avoid reusing temporary passwords for long periods.
- Use update mode only when you intend to modify existing users.
- Keep a copy of command output for audit/reference.

## 13) Quick command cheat sheet

Dry run only:

```bash
python src/manage.py seed_students data/sample_students.csv --dry-run --default-password=ChangeMe123!
```

Create users:

```bash
python src/manage.py seed_students data/sample_students.csv --default-password=ChangeMe123!
```

Update existing users:

```bash
python src/manage.py seed_students data/sample_students.csv --update
```

Create/update + send emails:

```bash
python src/manage.py seed_students data/sample_students.csv \
  --default-password=ChangeMe123! \
  --send-welcome \
  --site-domain=assess.langcen.cam.ac.uk \
  --use-https
```
