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
DATA_DIR = BASE_DIR.parent / "dados"
DB_PATH = DATA_DIR / "simplebd"
DATABASE_URL = f"sqlite:///{DB_PATH}"
CREDENTIAL_KEY_FILE = DATA_DIR / ".totem_cred_key"

# API SimpleSfique (login + sincronização no mesmo host)
# Base SEM /api/v1 — ex.: http://192.168.10.100:9005
def _env_url(*keys: str, default: str) -> str:
    for key in keys:
        raw = os.getenv(key)
        if raw and raw.strip():
            return raw.strip().rstrip("/")
    return default.rstrip("/")


URL_API: str = _env_url("URL_API", "URL_API_TOKEN", "URL_API_SINC", default="http://192.168.10.100:9005")


def api_v1_url(path: str) -> str:
    """Monta URL /api/v1/... sem duplicar o prefixo se URL_API já o incluir."""
    segment = path.strip("/")
    base = URL_API
    if base.endswith("/api/v1"):
        return f"{base}/{segment}"
    return f"{base}/api/v1/{segment}"

# CliSiTef / PIX
SITEF_IP: str = os.getenv("SITEF_IP", "192.168.10.12")
SITEF_ID_LOJA: str = os.getenv("SITEF_ID_LOJA", "00000000")
SITEF_ID_TERMINAL: str = os.getenv("SITEF_ID_TERMINAL", "ST000001")
SITEF_OPERADOR: str = os.getenv("SITEF_OPERADOR", "01")
SITEF_CNPJ_AUTOMACAO: str = os.getenv("SITEF_CNPJ_AUTOMACAO", "12523654185985")

