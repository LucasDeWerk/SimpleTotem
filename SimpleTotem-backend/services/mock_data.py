"""Dados mockados da API externa SimpleSfique.

Este backend não consome mais nenhuma API externa (exceto a comunicação real
com o pinpad/CliSiTef via services/sitef_*, que permanece intacta para a
homologação Fiserv). Todo dado que antes vinha de `URL_API` é gerado aqui,
mantendo o mesmo formato de resposta esperado pelos consumidores.
"""

from datetime import datetime
from typing import Any, Dict

from jose import jwt

MOCK_ID_SAAS = 1
MOCK_ID_EMPRESA = 1

MOCK_EMPRESA: Dict[str, Any] = {
    "id_saas": MOCK_ID_SAAS,
    "id_empresa": MOCK_ID_EMPRESA,
    "id": MOCK_ID_EMPRESA,
    "razao_social": "SimpleTotem Demonstração Ltda",
    "nome_fantasia": "SimpleTotem Demo",
    "cpf_cnpj": "12345678000190",
    "whatsapp": "5511999999999",
    "integrado_simplesfique": "S",
    "dhinc": "2024-01-01",
    "endereco": "Av. Homologação",
    "numero": "1000",
    "cep": "01310100",
    "cidade": "São Paulo",
    "id_uf": "SP",
    "id_ibge": "3550308",
    "id_bairro": 1,
    "bairro": "Centro",
    "perfil": "M",
    "crt": "3",
    "ind_tp_ativ": 0,
    "cnae": "5611203",
    "ret": "N",
    "token": None,
    "insc_estadual": "ISENTO",
}


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def mock_jwt(**claims: Any) -> str:
    """Gera um JWT bem-formado (não usado para autenticação real) apenas para
    manter compatível a decodificação não-verificada usada no fluxo de login."""
    payload = {"id_saas": MOCK_ID_SAAS, "id_empresa": MOCK_ID_EMPRESA, **claims}
    return jwt.encode(payload, "mock-secret-nao-usado-para-seguranca", algorithm="HS256")


def mock_login_response(email: str) -> Dict[str, Any]:
    token = mock_jwt(sub=email)
    return {
        "token": token,
        "tipo_token": "bearer",
        "expira_em": 86400,
        "saas": {"id_saas": MOCK_ID_SAAS, "nome": "SimpleTotem Demo SaaS"},
        "usuario": {"email": email, "nome": email.split("@")[0].title(), "id_empresa": MOCK_ID_EMPRESA},
        "empresas": [dict(MOCK_EMPRESA)],
    }


def mock_empresas_delta_payload() -> Dict[str, Any]:
    return {"data": [dict(MOCK_EMPRESA)], "records": 1}


def mock_terminal_validar_senha_response(terminal_id: int) -> Dict[str, Any]:
    return {
        "access_token": mock_jwt(terminal_id=terminal_id),
        "terminal": {
            "id": terminal_id,
            "nome": f"Totem Homologação {terminal_id:02d}",
            "codigo": f"T{terminal_id:02d}",
            "emite_cupom_fiscal": False,
        },
    }
