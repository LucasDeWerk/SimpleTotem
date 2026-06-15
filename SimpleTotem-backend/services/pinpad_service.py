"""Pinpad — genérico via device_service."""

from services import device_service


def sudo_sem_senha_disponivel() -> bool:
    return device_service.sudo_sem_senha_disponivel()


def status_pinpad() -> dict:
    return device_service.status_categoria("terminal_pagamento")


def configurar_pinpad(**_) -> dict:
    return device_service.status_categoria("terminal_pagamento")


def garantir_pinpad_configurado() -> str:
    import sys
    from pathlib import Path

    script_dir = Path(__file__).resolve().parent.parent.parent / "script"
    sys.path.insert(0, str(script_dir))
    from pinpad_config import garantir_configurado
    return garantir_configurado()


def bootstrap_permissoes_pinpad() -> dict:
    return device_service.status_categoria("terminal_pagamento")


def comando_worker_sitef() -> list[str]:
    import sys
    from pathlib import Path

    worker_sh = Path(__file__).resolve().parent.parent.parent / "script" / "run_sitef_worker.sh"
    if sudo_sem_senha_disponivel() and worker_sh.exists():
        return ["sudo", "-n", str(worker_sh)]
    return [sys.executable, str(Path(__file__).resolve().parent / "sitef_worker.py")]
