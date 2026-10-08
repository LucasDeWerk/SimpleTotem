"""Sessões de execução de funções administrativas/de teste CliSiTef (Roteiro
de Pré-Homologação Fiserv — Menu Administrativo 110 e, se necessário, outras
funções via código livre), rodadas de forma interativa a partir do painel
admin. Mesmo padrão de sitef_session.py, mas separado das sessões de venda."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class SessaoFuncaoAdmin:
    execucao_id: str
    funcao: str
    status: str = "processando"  # processando | finalizada | erro
    mensagens: List[Dict[str, Any]] = field(default_factory=list)
    prompt_pendente: Optional[Dict[str, Any]] = None
    resultado: Optional[Dict[str, Any]] = None
    erro: Optional[str] = None
    criada_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizada_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "execucao_id": self.execucao_id,
            "funcao": self.funcao,
            "status": self.status,
            "mensagens": list(self.mensagens),
            "prompt_pendente": self.prompt_pendente,
            "resultado": self.resultado,
            "erro": self.erro,
        }


class HomologacaoSessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessaoFuncaoAdmin] = {}
        self._lock = threading.Lock()

    def criar(self, funcao: str) -> SessaoFuncaoAdmin:
        execucao_id = str(uuid.uuid4())
        sessao = SessaoFuncaoAdmin(execucao_id=execucao_id, funcao=funcao)
        with self._lock:
            self._sessions[execucao_id] = sessao
        return sessao

    def obter(self, execucao_id: str) -> Optional[SessaoFuncaoAdmin]:
        with self._lock:
            return self._sessions.get(execucao_id)

    def atualizar_evento(self, execucao_id: str, evento: dict) -> None:
        sessao = self.obter(execucao_id)
        if not sessao:
            return

        tipo = evento.get("evento")
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            sessao.atualizada_em = now

            if tipo == "iniciada":
                sessao.mensagens.append({
                    "tipo": "info",
                    "texto": f"Função {evento.get('funcao')} iniciada (cupom {evento.get('cupom')})",
                })

            elif tipo == "mensagem":
                sessao.mensagens.append({
                    "tipo": "mensagem",
                    "texto": evento.get("texto", ""),
                    "destino": evento.get("destino"),
                    "tipo_campo": evento.get("tipo_campo"),
                })

            elif tipo == "prompt":
                prompt = {k: v for k, v in evento.items() if k != "evento"}
                sessao.prompt_pendente = prompt
                sessao.mensagens.append({"tipo": "prompt", **prompt})

            elif tipo == "prompt_resolvido":
                sessao.prompt_pendente = None

            elif tipo == "finalizada":
                sessao.status = "finalizada"
                sessao.resultado = {k: v for k, v in evento.items() if k != "evento"}
                sessao.mensagens.append({
                    "tipo": "resultado",
                    "aprovada": evento.get("aprovada"),
                    "resultado": evento.get("resultado"),
                    "mensagem_resultado": evento.get("mensagem_resultado"),
                })

    def finalizar_com_erro(self, execucao_id: str, erro: str) -> None:
        sessao = self.obter(execucao_id)
        if not sessao:
            return
        with self._lock:
            sessao.status = "erro"
            sessao.erro = erro
            sessao.prompt_pendente = None
            sessao.atualizada_em = datetime.now(timezone.utc).isoformat()
            sessao.mensagens.append({"tipo": "erro", "texto": erro})


store = HomologacaoSessionStore()
