import os
import sys

# Ensure repo root is on PYTHONPATH on Vercel
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.main import app  # noqa: E402
