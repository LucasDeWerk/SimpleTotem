"""Impressora — genérica via device_service."""

from services import device_service


def sudo_sem_senha_disponivel() -> bool:
    return device_service.sudo_sem_senha_disponivel()


def _motivo_indisponivel(st: dict) -> str | None:
    """Primeiro motivo que impede imprimir, ou None se está tudo certo."""
    if not st.get("configurado"):
        return "nao_configurada"
    if not st.get("conectado"):
        return "desconectada"
    if not st.get("acesso_ok"):
        return "sem_permissao"
    return None


# driver_id existe só por compatibilidade com as rotas antigas, que passam o
# parâmetro posicionalmente (a assinatura anterior, `(**_)`, rejeitava isso e
# fazia GET /hardware/impressora/status responder 500 sempre).
def status_impressora(driver_id: str | None = None, **_) -> dict:
    """Status da impressora para o bloqueio de venda sem comprovante.

    `papel_ok` é sempre None aqui: este backend não fala USB com a impressora
    (só checa presença/permissão via sysfs, ver script/hardware.py). Quem
    consegue ler o sensor de papel (ESC/POS DLE EOT 4) é o processo Electron,
    que já detém o canal USB — ver electron/printer.js.
    """
    st = device_service.status_categoria("impressora")
    motivo = _motivo_indisponivel(st)
    st["papel_ok"] = None
    st["pronta"] = motivo is None
    st["motivo_indisponivel"] = motivo
    return st


def configurar_impressora(driver_id: str | None = None, **_) -> dict:
    return device_service.status_categoria("impressora")


def bootstrap_permissoes_impressora() -> dict:
    return device_service.status_categoria("impressora")
