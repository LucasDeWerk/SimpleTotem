import secrets
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# JWT
SECRET_KEY: str = secrets.token_hex(32)  # Replace with a fixed value in production
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

# Database
# Resolve path: goes up one level from SimpleTotem-backend/ into dados/
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR.parent / "dados" / "simplebd"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# External API
URL_API_TOKEN: str = os.getenv("URL_API_TOKEN", "http://192.168.10.100:9005")
URL_API_SINC: str = os.getenv("URL_API_SINC", "http://192.168.10.100:9011")

