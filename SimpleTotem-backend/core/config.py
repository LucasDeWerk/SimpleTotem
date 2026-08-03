import secrets
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# ── Resolução de caminhos (dev vs PyInstaller frozen) ─────────────────────────
#
# Estrutura de produção esperada:
#   /opt/simpletotem/
#   ├── SimpleTotem-backend   ← sys.executable quando frozen
#   ├── SimpleTotem.AppImage
#   ├── dados/
#   └── script/
#
# Em dev: __file__ = .../SimpleTotem-backend/core/config.py
# Frozen: sys.executable = .../SimpleTotem-backend (o binário)

if getattr(sys, "frozen", False):
    # Rodando como binário PyInstaller — caminhos relativos ao executável
    _INSTALL_DIR = Path(sys.executable).resolve().parent
else:
    # Dev — sobe de core/ → SimpleTotem-backend/ → raiz do projeto
    _INSTALL_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR: Path = _INSTALL_DIR / "dados"
SCRIPT_DIR: Path = _INSTALL_DIR / "script"

# ── .env — carrega da raiz de instalação primeiro, fallback para diretório local ──
# O técnico pode editar o .env na raiz sem precisar abrir o bundle.
load_dotenv(dotenv_path=_INSTALL_DIR / ".env", override=False)
load_dotenv(override=False)

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = DATA_DIR / "simplebd"
DATABASE_URL = f"sqlite:///{DB_PATH}"
CREDENTIAL_KEY_FILE = DATA_DIR / ".totem_cred_key"

# ── SECRET_KEY persistente ────────────────────────────────────────────────────
# Gerado uma única vez e salvo em dados/.backend_secret.
# Sem isso, toda reinicialização do backend invalida os tokens JWT ativos.
_SECRET_KEY_FILE = DATA_DIR / ".backend_secret"


def _load_or_create_secret() -> str:
    if _SECRET_KEY_FILE.exists():
        return _SECRET_KEY_FILE.read_text().strip()
    key = secrets.token_hex(32)
    _SECRET_KEY_FILE.write_text(key)
    try:
        _SECRET_KEY_FILE.chmod(0o600)
    except Exception:
        pass
    return key


SECRET_KEY: str = _load_or_create_secret()
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 dia

# ── CliSiTef / PIX ────────────────────────────────────────────────────────────
SITEF_IP: str = os.getenv("SITEF_IP", "192.168.10.12")
SITEF_ID_LOJA: str = os.getenv("SITEF_ID_LOJA", "00000000")


def _validar_id_terminal(valor: str) -> None:
    """Roteiro de pré-homologação Fiserv: a faixa SE000900-SE000999 é
    reservada e não pode ser usada como SITEF_ID_TERMINAL em produção."""
    if valor.strip().upper().startswith("SE0009"):
        raise RuntimeError(
            f"SITEF_ID_TERMINAL não pode estar na faixa reservada SE000900-SE000999 "
            f"(valor atual: {valor}). Configure um ID de terminal válido no .env."
        )


SITEF_ID_TERMINAL: str = os.getenv("SITEF_ID_TERMINAL", "ST000001")
_validar_id_terminal(SITEF_ID_TERMINAL)
SITEF_OPERADOR: str = os.getenv("SITEF_OPERADOR", "01")
SITEF_CNPJ_AUTOMACAO: str = os.getenv("SITEF_CNPJ_AUTOMACAO", "12523654185985")
SITEF_PORTA_PINPAD: str = os.getenv("SITEF_PORTA_PINPAD", "AUTO_USB")
# Token TLS Fiserv — fornecido durante o processo de homologação; vazio = sem TLS
SITEF_TLS_TOKEN: str = os.getenv("SITEF_TLS_TOKEN", "")
# Senha do supervisor para funções administrativas (110, 123, etc.)
SITEF_SUPERVISOR_SENHA: str = os.getenv("SITEF_SUPERVISOR_SENHA", "000000")
