"""Controle local de vendas enviadas à Ticketera.

A API não deduplica `idempotency_key`; reenviar cria outra venda. Este registro
(JSON, não SQLite) guarda a resposta das vendas gravadas ("ok") e marca como
"incerto" as que falharam com 5xx/timeout, para conferir na Ticketera antes de
qualquer reenvio.
"""

import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.config import DATA_DIR

ARQUIVO = DATA_DIR / "ticketera_vendas.json"
_lock = threading.Lock()


def _ler() -> Dict[str, Any]:
    try:
        return json.loads(ARQUIVO.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def obter(chave: str) -> Optional[Dict[str, Any]]:
    with _lock:
        return _ler().get(chave)


def gravar(chave: str, registro: Dict[str, Any]) -> None:
    with _lock:
        dados = _ler()
        dados[chave] = registro
        ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def agora_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def total_venda(body: Dict[str, Any]) -> float:
    bruto = sum(float(i.get("quantidade") or 0) * float(i.get("valor_unitario") or 0) for i in body.get("itens", []))
    return round(bruto - float(body.get("desconto") or 0) + float(body.get("acrescimo") or 0), 2)
