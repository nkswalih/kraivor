"""
Kraivor Identity Service — Custom Admin Site Configuration

Brands the Django admin interface and configures global admin settings.
"""

from django.contrib import admin

# ---------------------------------------------------------------------------
# Admin Site Branding
# ---------------------------------------------------------------------------

admin.site.site_header = "Kraivor Identity Administration"
admin.site.site_title = "Kraivor Auth Admin"
admin.site.index_title = "Identity Service Dashboard"

# ---------------------------------------------------------------------------
# Unregister default models we don't need in the admin
# ---------------------------------------------------------------------------

# We manage users via our custom User admin, so unregister the default
# auth.User to avoid confusion.

# Keep Group management (useful for permissions)
# Unregister default User — our apps/users/admin.py registers the custom User

# ---------------------------------------------------------------------------
# Custom AdminSite class (optional — for future extensions)
# ---------------------------------------------------------------------------

class KraivorAdminSite(admin.AdminSite):
    """
    Custom admin site for Kraivor Identity Service.

    Provides:
    - Branded header and title
    - Custom index template (future)
    - Centralized admin configuration
    """

    site_header = "Kraivor Identity Administration"
    site_title = "Kraivor Auth Admin"
    index_title = "Identity Service Dashboard"


# Create the custom admin site instance
kraivor_admin = KraivorAdminSite(name="kraivor_admin")
