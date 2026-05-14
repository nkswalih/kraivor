#!/usr/bin/env python
import os
import sys
from pathlib import Path

# Add project root and apps directory to Python path
auth_dir = Path(__file__).resolve().parent
apps_dir = auth_dir / 'apps'
project_root = auth_dir.parent

# Set up paths in correct order
paths_to_add = [str(project_root), str(apps_dir)]
for p in paths_to_add:
    if p not in sys.path:
        sys.path.insert(0, p)

# Only set default settings module if not already specified
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'auth.settings.development'


def main():
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