from import_export import fields, resources

from .models import User


class UserResource(resources.ModelResource):
    email = fields.Field(attribute="email", column_name="email")
    # show date_joined only when exporting
    date_joined = fields.Field(attribute="date_joined", column_name="date_joined", readonly=True)

    class Meta:
        model = User
        # use email as the unique key when importing (updates instead of dupes)
        import_id_fields = ("email",)
        # include date_joined in exports, but since it's readonly it will be ignored on import
        fields = (
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "date_joined",
        )
        export_order = (
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "date_joined",
        )
