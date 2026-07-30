"""Pinpad — genérico via device_service."""

from core.config import SCRIPT_DIR
from services import device_service


def sudo_sem_senha_disponivel() -> bool:
    return device_service.sudo_sem_senha_disponivel()


def status_pinpad() -> dict:
    return device_service.status_categoria("terminal_pagamento")


def configurar_pinpad(**_) -> dict:
    return device_service.status_categoria("terminal_pagamento")


def garantir_pinpad_configurado() -> str:
    import sys

    sys.path.insert(0, str(SCRIPT_DIR))
    from pinpad_config import garantir_configurado
    return garantir_configurado()


def bootstrap_permissoes_pinpad() -> dict:
    return device_service.status_categoria("terminal_pagamento")


def comando_worker_sitef() -> list[str]:
    import sys
    from pathlib import Path

    worker_sh = SCRIPT_DIR / "run_sitef_worker.sh"
    if sudo_sem_senha_disponivel() and worker_sh.exists():
        return ["sudo", "-n", str(worker_sh)]

    # Frozen binary: roda o mesmo executável em modo worker
    if getattr(sys, "frozen", False):
        return [sys.executable, "--sitef-worker"]

    # Dev: executa sitef_worker.py com o Python atual
    worker_py = Path(__file__).resolve().parent / "sitef_worker.py"
    return [sys.executable, str(worker_py)]
