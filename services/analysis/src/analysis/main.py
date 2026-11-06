"""App entry point for uvicorn."""

from analysis.api.main import create_app

app = create_app()
