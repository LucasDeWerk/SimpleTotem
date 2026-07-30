"""Impressora — genérica via device_service."""

from services import device_service


def sudo_sem_senha_disponivel() -> bool:
    return device_service.sudo_sem_senha_disponivel()


def status_impressora(**_) -> dict:
    return device_service.status_categoria("impressora")


def configurar_impressora(**_) -> dict:
    return device_service.status_categoria("impressora")


def bootstrap_permissoes_impressora() -> dict:
    return device_service.status_categoria("impressora")
