from sqlalchemy import Column, Integer, Text, Numeric, LargeBinary
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


class Grupo(Base):
    __tablename__ = "test_grupo"

    id_grupo = Column(Integer, primary_key=True)
    descgrupo = Column(Text)
    foto = Column(LargeBinary)


class Subgrupo(Base):
    __tablename__ = "test_subgrupo"

    id_grupo = Column(Integer, primary_key=True)
    id_subgrupo = Column(Integer, primary_key=True)
    descsubgrupo = Column(Text)


class Marca(Base):
    __tablename__ = "test_marca"

    id_marca = Column(Integer, primary_key=True)
    descmarca = Column(Text)


class Medida(Base):
    __tablename__ = "test_medida"

    id_medida = Column(Integer, primary_key=True)
    descmedida = Column(Text)
    abreviatura = Column(Text)


class Produto(Base):
    __tablename__ = "test_produto"

    id_produto = Column(Integer, primary_key=True)
    gtin = Column(Text)
    cod_referencia = Column(Text)
    cod_fabricacao = Column(Text)
    descproduto = Column(Text)
    id_grupo = Column(Integer)
    id_subgrupo = Column(Integer)
    id_marca = Column(Integer)
    id_medida = Column(Integer)
    preco_venda = Column(Numeric)
    custo_medio = Column(Numeric)
    custo_aquisicao = Column(Numeric)
    custo_compra = Column(Numeric)
    peso = Column(Numeric)
    id_ncm = Column(Text)
    cest = Column(Text)
    foto = Column(LargeBinary)
    estoque = Column(Numeric)
    dhinc = Column(Text)
    dhalt = Column(Text)


class TipoPagamento(Base):
    __tablename__ = "tfin_tipopagrec"

    id = Column(Text, primary_key=True)
    desctipopagrec = Column(Text)


class Saida(Base):
    __tablename__ = "tven_saida"

    id = Column(Integer, primary_key=True)
    dtemissao = Column(Text)
    id_cfop = Column(Text)
    id_clifor = Column(Integer)
    id_vendedor = Column(Integer)
    situacao = Column(Text)
    vlr_venda = Column(Numeric)
    custo_total_venda = Column(Numeric)
    id_terminal = Column(Integer)


class SaidaPagamento(Base):
    __tablename__ = "tven_saidapagamento"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_saida = Column(Integer, nullable=False)
    id_tipo_pagamento = Column(Text)
    vlr_pagamento = Column(Numeric, nullable=False)
    nsu_sitef = Column(Text)
    nsu_host = Column(Text)
    autorizacao = Column(Text)
    bandeira = Column(Text)
    modalidade = Column(Text)
    pix = Column(Integer, nullable=False, default=0)
    cupom_bruto = Column(Text)
    dh_pagamento = Column(Text, nullable=False)


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


class SaidaItem(Base):
    __tablename__ = "tven_saidaitens"

    id = Column(Integer, primary_key=True)
    id_saida = Column(Integer)
    id_produto = Column(Integer)
    vlr_unitario_sugerido = Column(Numeric)
    vlr_unitario_praticado = Column(Numeric)
    desconto_unit_item = Column(Numeric)
    acrescimo_unit_item = Column(Numeric)
    quantidade = Column(Numeric)
    vlr_total_item = Column(Numeric)


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


class SyncCheckpoint(Base):
    """Última data de sincronização delta por etapa."""
    __tablename__ = "tconf_sync_checkpoint"

    etapa = Column(Text, primary_key=True)
    dhsinc = Column(Text)
    ultimo_records = Column(Integer)
    dh_sync = Column(Text)

