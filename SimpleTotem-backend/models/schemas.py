from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Hardware (psutil) ─────────────────────────────────────────────────────────

class CPUInfo(BaseModel):
    usage_percent: float
    core_count: int
    frequency_mhz: float


class MemoryInfo(BaseModel):
    total_mb: float
    available_mb: float
    used_mb: float
    usage_percent: float


class DiskInfo(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    usage_percent: float


# ── Empresa ───────────────────────────────────────────────────────────────────

class EmpresaOut(BaseModel):
    id_saas: int
    id_empresa: Optional[int] = None
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    whatsapp: Optional[str] = None
    cidade: Optional[str] = None
    id_uf: Optional[str] = None
    endereco: Optional[str] = None
    numero: Optional[str] = None
    cep: Optional[str] = None
    bairro: Optional[str] = None
    token: Optional[str] = None

    class Config:
        from_attributes = True


# ── Catálogo ──────────────────────────────────────────────────────────────────

class GrupoOut(BaseModel):
    id_grupo: int
    descgrupo: Optional[str] = None

    class Config:
        from_attributes = True


class SubgrupoOut(BaseModel):
    id_grupo: int
    id_subgrupo: int
    descsubgrupo: Optional[str] = None

    class Config:
        from_attributes = True


class ProdutoOut(BaseModel):
    id_produto: int
    descproduto: Optional[str] = None
    cod_referencia: Optional[str] = None
    id_grupo: Optional[int] = None
    id_subgrupo: Optional[int] = None
    id_medida: Optional[int] = None
    preco_venda: Optional[float] = None
    estoque: Optional[float] = None
    dhinc: Optional[str] = None
    dhalt: Optional[str] = None

    class Config:
        from_attributes = True


# ── Vendas ────────────────────────────────────────────────────────────────────

class SaidaItemOut(BaseModel):
    id: int
    id_saida: int
    id_produto: Optional[int] = None
    vlr_unitario_praticado: Optional[float] = None
    quantidade: Optional[float] = None
    vlr_total_item: Optional[float] = None

    class Config:
        from_attributes = True


class SaidaOut(BaseModel):
    id: int
    dtemissao: Optional[str] = None
    situacao: Optional[str] = None
    vlr_venda: Optional[float] = None

    class Config:
        from_attributes = True


class TipoPagamentoOut(BaseModel):
    id: str
    desctipopagrec: Optional[str] = None

    class Config:
        from_attributes = True


# ── Métodos de Pagamento ──────────────────────────────────────────────────────

class MetodoPagamentoOut(BaseModel):
    type: str           # credit | debit | pix | cash
    label: str
    icon: str
    available: bool = True


# ── Hardware (DB) ─────────────────────────────────────────────────────────────

class HardwareDBOut(BaseModel):
    id: int
    tipo_dispositivo: Optional[str] = None
    nome: Optional[str] = None
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    descricao: Optional[str] = None
    ativo: Optional[int] = None
    dhinc: Optional[str] = None
    dhalt: Optional[str] = None

    class Config:
        from_attributes = True


class HardwareDBCreate(BaseModel):
    tipo_dispositivo: str
    nome: str
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    descricao: Optional[str] = None
    ativo: int = 1


class HardwareDBUpdate(BaseModel):
    nome: Optional[str] = None
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    descricao: Optional[str] = None
    ativo: Optional[int] = None


# ── Inicia Venda ──────────────────────────────────────────────────────────────

class ItemVendaIn(BaseModel):
    produto_id: int
    descricao: Optional[str] = None
    quantidade: float
    preco_unitario: float


class ItemVendaCalculado(BaseModel):
    produto_id: int
    descricao: Optional[str] = None
    quantidade: float
    preco_unitario: float
    total_item: float


class IniciaVendaRequest(BaseModel):
    itens: List[ItemVendaIn]


class IniciaVendaResponse(BaseModel):
    subtotal: float
    desconto: float
    total: float
    itens: List[ItemVendaCalculado]


# ── Inicia Transação ──────────────────────────────────────────────────────────

class IniciaTransacaoRequest(BaseModel):
    itens: List[ItemVendaIn]
    total_cliente: float          # total retornado por /iniciavenda
    metodo_pagamento_id: str      # id de tfin_tipopagrec
    cupom: Optional[str] = None   # gerado automaticamente se None


class IniciaTransacaoResponse(BaseModel):
    status: str                   # "aprovada" | "negada"
    id_venda: Optional[int] = None
    nsu_sitef: str
    nsu_host: str
    autorizacao: str
    modalidade: str
    bandeira: str
    total_cobrado: float
    linhas_cupom: List[str]
    mensagem: Optional[str] = None


