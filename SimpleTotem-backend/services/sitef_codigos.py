"""Tradução dos códigos de retorno da CliSiTef, para uso em logs e mensagens
de UI — traduz o código numérico retornado por
ConfiguraIntSiTefInterativo(Ex)A / IniciaFuncaoSiTefInterativoA /
ContinuaFuncaoSiTefInterativoA / FinalizaFuncaoSiTefInterativoA em texto
legível. Fonte: tabela repassada pelo usuário (documentação/suporte técnico
Fiserv)."""

from __future__ import annotations

# Retornados por ConfiguraIntSiTefInterativo(Ex)A — códigos positivos.
ERROS_CONFIGURA: dict[int, str] = {
    1: "Endereço IP inválido ou não resolvido",
    2: "Código da loja inválido",
    3: "Código de terminal inválido",
    6: "Erro na inicialização do TCP/IP",
    7: "Falta de memória",
    8: "CliSiTef não encontrada ou com problemas",
    9: "Configuração de servidores SiTef excedida",
    10: "Erro de acesso na pasta CliSiTef (verifique permissões)",
    11: "Dados inválidos passados pela automação",
    12: "Modo seguro não ativo (arquivo .cha ausente no servidor)",
    13: "Caminho DLL inválido (path das bibliotecas muito grande)",
}

# Retornados por Inicia/Continua/FinalizaFuncaoSiTefInterativo —
# majoritariamente negativos.
ERROS_GERAIS: dict[int, str] = {
    -1: "Módulo não inicializado — chame ConfiguraInt primeiro",
    -2: "Operação cancelada pelo operador",
    -3: "Função/modalidade inexistente ou inválida",
    -4: "Falta de memória no PDV",
    -5: "Sem comunicação com o SiTef",
    -6: "Operação cancelada pelo usuário no pinpad",
    -8: "CliSiTef desatualizada — função não implementada",
    -9: "ContinuaFuncao chamada sem IniciaFuncao",
    -10: "Parâmetro obrigatório não passado",
    -12: "Loop anterior não terminou (retorno 10000 não atingido)",
    -13: "Documento fiscal não encontrado",
    -15: "Operação cancelada pela automação",
    -20: "Parâmetro inválido para a função",
    -21: "Palavra proibida usada em coleta aberta (ex: SENHA)",
    -25: "Erro no Correspondente Bancário — realizar sangria",
    -30: "Erro de acesso ao arquivo (verifique permissões leitura/escrita)",
    -40: "Transação negada pelo servidor SiTef",
    -41: "Dados inválidos",
    -43: "Problema na execução de rotina no pinpad",
    -50: "Transação não segura",
    -100: "Erro interno do módulo",
}


def descrever_erro_configura(codigo: int) -> str:
    return ERROS_CONFIGURA.get(codigo, f"Código {codigo} (desconhecido)")


def descrever_erro_geral(codigo: int) -> str:
    return ERROS_GERAIS.get(codigo, f"Código {codigo} (desconhecido)")


# Exigência Fiserv: exibir os códigos/mensagens retornados sem alteração. Em
# ConfiguraIntSiTefInterativo(Ex)A e IniciaFuncaoSiTefInterativoA, a CliSiTef
# não manda NENHUM texto quando falha nesse ponto — só o código numérico puro
# (confirmado: não existe função na libclisitef.so que devolva uma mensagem
# para esses casos). Por isso o código vem em destaque (dado literal
# retornado pela CliSiTef) e nossa tradução aparece claramente rotulada como
# "descrição interna" — nunca atribuída à CliSiTef, para não virar paráfrase
# disfarçada de mensagem original perante auditoria.

def formatar_codigo_configura(codigo: int) -> str:
    descricao = ERROS_CONFIGURA.get(codigo)
    if descricao is None:
        return f"Código {codigo} retornado pela CliSiTef (sem descrição mapeada)"
    return f"Código {codigo} retornado pela CliSiTef (descrição interna: {descricao})"


def formatar_codigo_geral(codigo: int) -> str:
    descricao = ERROS_GERAIS.get(codigo)
    if descricao is None:
        return f"Código {codigo} retornado pela CliSiTef (sem descrição mapeada)"
    return f"Código {codigo} retornado pela CliSiTef (descrição interna: {descricao})"
