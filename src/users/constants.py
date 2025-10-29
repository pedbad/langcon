# src/users/constants.py

# Password reset template paths used by users.views.*
# All files live under users/templates/users/registration/
PWD_RESET_TPLS = {
    # Web pages
    "form": "users/registration/password_reset_form.html",
    "done": "users/registration/password_reset_done.html",
    "confirm": "users/registration/password_reset_confirm.html",
    "complete": "users/registration/password_reset_complete.html",
    # Emails
    "email_txt": "users/registration/password_reset_email.txt",
    "email_html": "users/registration/password_reset_email.html",  # present
    "subject": "users/registration/password_reset_subject.txt",
}
