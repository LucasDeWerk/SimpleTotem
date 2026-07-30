import logging

logger = logging.getLogger(__name__)


def authenticate_system_user(username: str, password: str) -> bool:
    """Valida usuário e senha contra as credenciais do sistema (PAM/Linux)."""
    username = (username or "").strip()
    if not username or not password:
        return False

    try:
        import pam
    except ImportError as exc:
        logger.error("Módulo python-pam não instalado: %s", exc)
        raise RuntimeError(
            "Autenticação do sistema indisponível. Instale python-pam no backend."
        ) from exc

    auth = pam.pam()
    ok = auth.authenticate(username, password)
    if not ok:
        logger.info("Falha de autenticação PAM para usuário: %s", username)
    return ok
