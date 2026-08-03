from sqlalchemy import Column, Integer, Text
from core.database import Base


class Empresa(Base):
    __tablename__ = "vstb_empresa"

    id_saas = Column(Integer, primary_key=True)
    id_empresa = Column(Integer, primary_key=True)
    razao_social = Column(Text, nullable=False)
    nome_fantasia = Column(Text, nullable=False)
    cpf_cnpj = Column(Text)
    whatsapp = Column(Text)
    integrado_simplesfique = Column(Text, nullable=False)
    dhinc = Column(Text, nullable=False)
    insc_estadual = Column(Text)
    endereco = Column(Text)
    numero = Column(Text)
    cep = Column(Text)
    id_ibge = Column(Text)
    cidade = Column(Text)
    id_uf = Column(Text)
    id_bairro = Column(Integer)
    bairro = Column(Text)
    perfil = Column(Text)
    crt = Column(Text)
    ind_tp_ativ = Column(Integer)
    cnae = Column(Text)
    ret = Column(Text)
    token = Column(Text)
    email_simples = Column(Text)
    senha_simples = Column(Text)
    usuario_os = Column(Text)
    senha_os = Column(Text)


class Terminal(Base):
    __tablename__ = "tven_terminal"

    id = Column(Integer, primary_key=True)
    descterminal = Column(Text, nullable=False)
    nome_dispositivo = Column(Text)
    ip_dispositivo = Column(Text)
    imp_nfe_nfce = Column(Text)
    imp_ipc_nfe_nfce = Column(Text)
    totem_autoatendimento = Column(Text, nullable=False)
    imprime_pedido = Column(Text, nullable=False)


class Hardware(Base):
    __tablename__ = "tconf_hardware"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_dispositivo = Column(Text)
    nome = Column(Text)
    vendor_id = Column(Text)
    product_id = Column(Text)
    descricao = Column(Text)
    driver_id = Column(Text)
    ativo = Column(Integer)
    dhinc = Column(Text)
    dhalt = Column(Text)


class ApiSessao(Base):
    """Sessão SimpleSfique + vínculo com usuário OS do totem."""
    __tablename__ = "tconf_api_sessao"

    chave = Column(Text, primary_key=True)
    token = Column(Text)
    id_saas = Column(Integer)
    id_empresa = Column(Integer)
    email = Column(Text)
    os_usuario = Column(Text)
    senha_simples_enc = Column(Text)
    senha_os_enc = Column(Text)
    expira_em = Column(Integer)
    dh_login = Column(Text)
    terminal_id = Column(Integer)
    terminal_token = Column(Text)
    senha_terminal_enc = Column(Text)


class SyncCheckpoint(Base):
    """Última data de sincronização delta por etapa."""
    __tablename__ = "tconf_sync_checkpoint"

    etapa = Column(Text, primary_key=True)
    dhsinc = Column(Text)
    ultimo_records = Column(Integer)
    dh_sync = Column(Text)

