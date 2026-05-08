#!/usr/bin/env python
import os
import sys
from pathlib import Path


def main():
    # Add apps/ to Python path so Django can import 'users', 'authentication', etc.
    apps_dir = Path(__file__).resolve().parent / 'apps'
    if str(apps_dir) not in sys.path:
        sys.path.insert(0, str(apps_dir))
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth.settings.development')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? "
            "Did you forget to activate a virtual environment?"
        ) from exc
    
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()