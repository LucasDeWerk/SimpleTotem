"""Mensagens legíveis para códigos de retorno CliSiTef."""

SITEF_ERROS = {
    -1: "Módulo não inicializado",
    -2: "Operação cancelada pelo operador",
    -3: "Função/modalidade inválida",
    -5: "Sem comunicação com o SiTef",
    -6: "Operação cancelada no pinpad",
    -24: "Carteira Digital/PIX não habilitada no servidor SiTef — solicite habilitação à Fiserv",
    -40: "Transação negada pelo servidor SiTef",
    -43: "Erro no pinpad — verifique conexão USB ou contate o suporte técnico",
}


def mensagem_resultado(codigo: int) -> str:
    return SITEF_ERROS.get(codigo, f"Código SiTef {codigo}")
