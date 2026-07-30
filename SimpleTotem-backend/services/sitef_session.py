"""Sessões de transação SiTef em memória — suporte a polling PIX/QR."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TransacaoSession:
    transacao_id: str
    status: str = "processando"
    mensagens: List[str] = field(default_factory=list)
    mensagem_atual: Optional[str] = None
    qrcode: Optional[str] = None
    qrcode_ativo: bool = False
    erro: Optional[str] = None
    resultado: Optional[Dict[str, Any]] = None
    contexto_venda: Optional[Dict[str, Any]] = None
    id_saida: Optional[int] = None
    persistida: bool = False
    confirmada: bool = False
    criada_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    atualizada_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        base = {
            "transacao_id": self.transacao_id,
            "status": self.status,
            "mensagens": list(self.mensagens),
            "mensagem_atual": self.mensagem_atual,
            "qrcode": self.qrcode,
            "qrcode_ativo": self.qrcode_ativo,
            "erro": self.erro,
            "id_venda": self.id_saida,
        }
        if self.resultado:
            base.update(self.resultado)
        return base


class TransacaoSessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, TransacaoSession] = {}
        self._lock = threading.Lock()

    def criar(self) -> TransacaoSession:
        tid = str(uuid.uuid4())
        session = TransacaoSession(transacao_id=tid)
        with self._lock:
            self._sessions[tid] = session
        return session

    def obter(self, transacao_id: str) -> Optional[TransacaoSession]:
        with self._lock:
            return self._sessions.get(transacao_id)

    def transacao_em_andamento(self) -> bool:
        with self._lock:
            return any(s.status == "processando" for s in self._sessions.values())

    def atualizar_evento(self, transacao_id: str, evento: dict) -> None:
        session = self.obter(transacao_id)
        if not session:
            return

        tipo = evento.get("evento")
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            session.atualizada_em = now

            if tipo == "mensagem":
                texto = evento.get("texto", "")
                if texto:
                    session.mensagem_atual = texto
                    if texto not in session.mensagens:
                        session.mensagens.append(texto)

            elif tipo == "qrcode":
                session.qrcode = evento.get("payload") or session.qrcode
                session.qrcode_ativo = True

            elif tipo == "qrcode_remover":
                session.qrcode_ativo = False

            elif tipo == "finalizada":
                codigo = evento.get("resultado")
                if evento.get("aprovada"):
                    session.status = "aprovada"
                else:
                    session.status = "negada"
                    if codigo is not None and not session.erro:
                        session.erro = f"Transação não aprovada (código {codigo})"
                session.qrcode_ativo = False
                if session.resultado is None:
                    session.resultado = {}
                if codigo is not None:
                    session.resultado["resultado_codigo"] = codigo

            elif tipo == "iniciada":
                session.status = "processando"

    def anexar_contexto_venda(self, transacao_id: str, contexto: Dict[str, Any]) -> None:
        session = self.obter(transacao_id)
        if not session:
            return
        with self._lock:
            session.contexto_venda = contexto

    def marcar_persistida(self, transacao_id: str, id_saida: int) -> None:
        session = self.obter(transacao_id)
        if not session:
            return
        with self._lock:
            session.id_saida = id_saida
            session.persistida = True

    def marcar_confirmada(self, transacao_id: str) -> None:
        session = self.obter(transacao_id)
        if not session:
            return
        with self._lock:
            session.confirmada = True

    def finalizar(self, transacao_id: str, resultado: Optional[dict] = None, erro: Optional[str] = None) -> None:
        session = self.obter(transacao_id)
        if not session:
            return

        with self._lock:
            session.atualizada_em = datetime.now(timezone.utc).isoformat()
            if erro:
                session.status = "erro"
                session.erro = erro
                session.qrcode_ativo = False
                return

            if resultado:
                session.resultado = {
                    "nsu_sitef": resultado.get("nsu_sitef", ""),
                    "nsu_host": resultado.get("nsu_host", ""),
                    "autorizacao": resultado.get("autorizacao", ""),
                    "modalidade": resultado.get("modalidade", ""),
                    "bandeira": resultado.get("bandeira", ""),
                    "linhas_cupom": resultado.get("linhas_cupom", []),
                    "cupom_bruto": resultado.get("cupom_bruto", ""),
                    "total_cobrado": resultado.get("total_cobrado"),
                    "pix": resultado.get("pix", False),
                    "resultado_codigo": resultado.get("resultado"),
                }
                session.status = "aprovada" if resultado.get("aprovada") else "negada"
                session.qrcode_ativo = False


store = TransacaoSessionStore()
