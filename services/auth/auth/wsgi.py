import os
import sys
from pathlib import Path

# Add apps/ to Python path
apps_dir = Path(__file__).resolve().parent.parent / 'apps'
if str(apps_dir) not in sys.path:
    sys.path.insert(0, str(apps_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth.settings.development')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()