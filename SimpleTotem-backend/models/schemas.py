from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TotemLoginRequest(BaseModel):
    usuario: str
    senha: str


class EmpresaStatusOut(BaseModel):
    configurada: bool


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


class SimpleSfiqueLoginRequest(BaseModel):
    email: str
    senha: str
    os_usuario: Optional[str] = None
    senha_os: Optional[str] = None


class SessaoSimpleSfiqueOut(BaseModel):
    id_saas: int
    id_empresa: int
    email: Optional[str] = None
    os_usuario: Optional[str] = None
    expira_em: Optional[int] = None
    dh_login: Optional[str] = None
    token_ativo: bool = True


class SimpleSfiqueLoginResponse(BaseModel):
    token_ok: bool = True
    requires_selection: bool = False
    expira_em: Optional[int] = None
    tipo_token: str = "bearer"
    sessao: Optional[SessaoSimpleSfiqueOut] = None
    empresa: Optional[EmpresaOut] = None
    empresas: List[EmpresaOut] = []
    usuario: Optional[Dict[str, Any]] = None
    saas: Optional[Dict[str, Any]] = None


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
    driver_id: Optional[str] = None
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
    driver_id: Optional[str] = None
    ativo: int = 1


class HardwareDBUpdate(BaseModel):
    nome: Optional[str] = None
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    descricao: Optional[str] = None
    driver_id: Optional[str] = None
    ativo: Optional[int] = None


class HardwareAtribuir(BaseModel):
    """Atribui qualquer dispositivo USB a uma categoria (marca agnóstico)."""
    categoria: str
    vendor_id: str
    product_id: str
    nome: str = ""
    fabricante: str = ""


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


class IniciaTransacaoStartResponse(BaseModel):
    transacao_id: str
    status: str = "processando"


class TransacaoStatusResponse(BaseModel):
    transacao_id: str
    status: str                   # processando | aprovada | negada | erro
    mensagens: List[str] = []
    mensagem_atual: Optional[str] = None
    qrcode: Optional[str] = None
    qrcode_ativo: bool = False
    erro: Optional[str] = None
    nsu_sitef: Optional[str] = None
    nsu_host: Optional[str] = None
    autorizacao: Optional[str] = None
    modalidade: Optional[str] = None
    bandeira: Optional[str] = None
    total_cobrado: Optional[float] = None
    linhas_cupom: List[str] = []
    cupom_bruto: Optional[str] = None
    pix: bool = False
    resultado_codigo: Optional[int] = None


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
    transacao_id: Optional[str] = None
    pix: bool = False


