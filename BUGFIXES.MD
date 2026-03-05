# Bug Fixes Log

## 2026-03-04 - Registration Password and Login Autofill Fix

### Symptoms
- Admin/Teacher could register a user, but that user could not log in with the entered password.
- Browser autofill sometimes treated USN/ADTIS as the login identifier.

### Root Cause
- Registration view explicitly called `set_unusable_password()` after form validation, which discarded the submitted password.
- Login/register autocomplete hints were not fully aligned for credential managers:
  - login identifier field was tagged as `email` instead of `username`
  - USN field had no explicit autocomplete policy

### Changes Made
- Updated registration flow to preserve the password entered in the form.
  - File: `src/users/views.py`
  - Removed `user.set_unusable_password()` in `RegisterView.form_valid`.
  - Updated success message to remove invite-email wording for this flow.
- Hardened credential autofill behavior.
  - File: `src/users/templates/users/registration/login.html`
  - Set login identifier autocomplete to `username` (while still using email as identifier value).
  - File: `src/users/templates/users/registration/register.html`
  - Set USN field autocomplete to `off`.
- Updated tests to match intended behavior.
  - File: `src/users/tests/test_register.py`
  - Registration test now expects a usable password and no invite email for this flow.

### Expected Result
- Users created via registration can log in immediately with the password set during registration.
- Browser/password-manager autofill is less likely to confuse USN with login identity.

## 2026-03-05 - Dashboard USN Missing for Teacher/Admin

### Symptoms
- USN values appeared in the admin-only Students page, but were missing (`—`) in the Teacher/Admin dashboard table.

### Root Cause
- Dashboard USN rendering and sorting relied only on `AssessmentEvaluation.student_usn` (snapshot field).
- For records where the evaluation snapshot USN was blank, the dashboard did not fall back to `Profile.student_number`.

### Changes Made
- Updated dashboard query to include profile relation and search fallback.
  - File: `src/assessor/views.py`
  - Added `user__profile` in `select_related(...)`.
  - Search now includes `user__profile__student_number`.
- Added robust USN fallback in dashboard row preparation.
  - File: `src/assessor/views.py`
  - New behavior: prefer `evaluation.student_usn`, fallback to `user.profile.student_number`.
  - Sorting now uses the resolved display USN value.
- Updated dashboard row template to render resolved USN value.
  - File: `src/assessor/templates/assessor/partials/assessment_table_row.html`
  - Uses `assessment.usn_display` instead of only `evaluation.student_usn`.
- Added regression test.
  - File: `src/assessor/tests.py`
  - Verifies dashboard shows profile USN when evaluation snapshot USN is blank.

### Expected Result
- Teacher and Admin dashboards now show USN consistently when profile data exists, even if evaluation snapshot USN is empty.
