from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from app import create_app
from app.services.digest_notifications import dispatch_pending_digest_notifications
from app.services.qsl_digest import run_due_qsl_digest_generation

app = create_app()

with app.app_context():
    generation = run_due_qsl_digest_generation()
    dispatch = dispatch_pending_digest_notifications(limit=10_000)
    print("generation:", generation)
    print("dispatch:", dispatch)
