# src/users/forms_invite.py
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm

UserModel = get_user_model()


class InvitePasswordResetForm(PasswordResetForm):
    """
    Like PasswordResetForm, but INCLUDE users with unusable passwords.
    Django's default excludes those (hence no email for fresh accounts).
    """

    def get_users(self, email):
        email_field = UserModel.get_email_field_name()
        # active users whose email matches (case-insensitive)
        qs = UserModel._default_manager.filter(**{f"{email_field}__iexact": email}, is_active=True)
        # New (Python 3+)
        yield from qs.iterator()
