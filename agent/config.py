"""Configuration for Google Flow Agent."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "flow_agent.db"
WS_HOST = "127.0.0.1"
WS_PORT = 9222  # Extension connects here
API_HOST = "0.0.0.0"
API_PORT = 8100
GOOGLE_FLOW_API = "https://aisandbox-pa.googleapis.com"
RECAPTCHA_SITE_KEY = "6LdsFiUsAAAAAIjVDZcuLhaHiDn5nnHVXVRQGeMV"
POLL_INTERVAL = 5  # seconds
MAX_RETRIES = 5
