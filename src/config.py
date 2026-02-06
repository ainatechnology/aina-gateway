"""Gateway configuration via environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

GATEWAY_HOST = os.getenv("GATEWAY_HOST", "127.0.0.1")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8008"))
API_KEY = os.getenv("API_KEY", "")
