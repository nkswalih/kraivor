"""App entry point for uvicorn."""
from app.api.main import create_app

app = create_app()
