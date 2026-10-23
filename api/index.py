"""Vercel entry point: exposes the FastAPI app as one Python serverless function.

vercel.json rewrites every /api/* request here; the app's own routes already
carry the /api prefix, so no path mangling is needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app  # noqa: E402, F401
