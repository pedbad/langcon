# src/users/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = "users:login"  # adjust to your named URL
    raise_exception = False  # set True if you prefer a 403 instead of redirect

    def test_func(self):
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return True
        # use your explicit role field for clarity
        return getattr(user, "role", None) == "admin"
