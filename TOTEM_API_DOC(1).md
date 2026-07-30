# API do Totem — SimplesFique

Documentação de integração para o desenvolvedor do totem executável consumir as APIs do backend.

**Base URL:** `http://192.168.10.51:8000/api/v1`  
**Formato:** JSON em todas as requisições e respostas  
**Header obrigatório em todas as chamadas:** `Accept: application/json`

---

## Índice

1. [Visão geral](#1-visão-geral)
2. [Fluxo de inicialização (obrigatório)](#2-fluxo-de-inicialização-obrigatório)
   - [2.1 Login do operador → JWT](#21-login-do-operador--jwt)
   - [2.2 Listar terminais ativos](#22-listar-terminais-ativos)
   - [2.3 Validar senha do terminal → terminal token](#23-validar-senha-do-terminal--terminal-token)
   - [2.4 GET completo da configuração do terminal](#24-get-completo-da-configuração-do-terminal)
3. [Fluxo de venda completa — `venda-completa`](#3-fluxo-de-venda-completa--venda-completa)
4. [Atualização periódica da config](#4-atualização-periódica-da-config)
5. [Fluxo de venda separado (alternativo)](#5-fluxo-de-venda-separado-alternativo)
6. [Referência de erros HTTP](#6-referência-de-erros-http)
7. [Tokens, headers e segurança](#7-tokens-headers-e-segurança)

---

## 1. Visão geral

O totem usa **dois tokens** em momentos diferentes:

| Variável local | Obtido em | Usado em |
|---|---|---|
| `jwt_token` | `POST /auth/login` | Listar terminais, validar senha |
| `terminal_token` | `POST /operacional/terminais/{id}/validar-senha` | Config, `venda-completa`, `pedido-finalizado` |

### Fluxo ideal (inicialização)

```
┌─────────────────────────────────────────────────────────────────┐
│  1. POST /auth/login                                            │
│     → salva jwt_token                                           │
├─────────────────────────────────────────────────────────────────┤
│  2. GET /operacional/terminais                                  │
│     → operador escolhe terminal → salva terminal_id             │
├─────────────────────────────────────────────────────────────────┤
│  3. POST /operacional/terminais/{terminal_id}/validar-senha     │
│     → salva terminal_token (app: "totem")                       │
├─────────────────────────────────────────────────────────────────┤
│  4. GET /totem/terminais/{terminal_id}/config                   │
│     → salva ambientes, menus, produtos, versões                 │
│     → verifica terminal.emite_cupom_fiscal                      │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo de venda (recomendado)

```
Cliente monta pedido no totem
        ↓
Pagamento aprovado pelo pinpad Fiserv
        ↓
POST /totem/venda-completa  [terminal_token]
        ↓
Exibe codigo_senha (+ cupom fiscal se emite_cupom_fiscal: true)
```

> **Recomendação:** use sempre `POST /totem/venda-completa`. Ela executa internamente cálculo fiscal, criação do pedido e emissão do cupom em uma única chamada, usando apenas o `terminal_token`.

### Estado que o totem deve persistir

| Variável | Quando salvar | Para que serve |
|---|---|---|
| `jwt_token` | Após login | Listar terminais e validar senha |
| `terminal_id` | Após escolha do operador | URLs de config e validação |
| `terminal_token` | Após validar senha | Todas as operações do totem |
| `config_version` | Após GET config | Polling sem re-download desnecessário |
| `produtos_version` | Após GET config | Polling sem re-download desnecessário |
| `emite_cupom_fiscal` | Após GET config | Saber se haverá cupom na resposta da venda |
| `idempotency_key` | Antes de cada venda | Evitar pedido duplicado em retry de rede |

---

## 2. Fluxo de inicialização (obrigatório)

Execute estas 4 etapas **na ordem** ao abrir o totem ou ao trocar de terminal.

---

### 2.1 Login do operador → JWT

Autentica o operador e retorna o JWT com `id_empresa` embutido (necessário para gerar o `terminal_token` com escopo fiscal).

```
POST /auth/login
```

**Headers:**
```
Accept: application/json
Content-Type: application/json
```

**Body:**
```json
{
  "email": "operador@suaempresa.com",
  "senha": "sua_senha"
}
```

**Resposta 200 — sucesso:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "tipo_token": "bearer",
  "expira_em": 86400,
  "usuario": {
    "id": 1,
    "id_saas": 1,
    "nome": "Operador",
    "email": "operador@suaempresa.com",
    "permite_consolidar": "N",
    "ativo": "S",
    "dhinc": "2026-01-15T10:00:00.000000Z",
    "dhalt": null
  },
  "saas": {
    "id": 1,
    "nome": "Minha Empresa SAAS",
    "email": "contato@empresa.com",
    "telefone": "11999999999",
    "dhinc": "2026-01-01T00:00:00.000000Z",
    "ativo": "S"
  },
  "empresas": [
    {
      "id": 1,
      "id_saas": 1,
      "razao_social": "Empresa Exemplo LTDA",
      "fantasia": "Loja Exemplo",
      "cpf_cnpj": "12345678000199",
      "ativo": "S"
    }
  ]
}
```

| Campo | Descrição |
|---|---|
| `token` | Salvar como `jwt_token`. Enviar em `Authorization: Bearer {jwt_token}` nas etapas 2 e 3 |
| `expira_em` | Validade em **segundos** (padrão: 86400 = 24h) |
| `empresas` | Lista de empresas do operador. O JWT já carrega a primeira empresa ativa como `id_empresa` |

**Respostas de erro:**

| HTTP | Body | Causa |
|---|---|---|
| `401` | `{ "erro": "Credenciais inválidas" }` | E-mail ou senha incorretos |
| `403` | `{ "erro": "Usuário inativo" }` | Conta desativada |
| `403` | `{ "erro": "Usuário sem empresa ativa vinculada" }` | Operador sem empresa |
| `422` | `{ "message": "...", "errors": { ... } }` | Validação (e-mail inválido, senha vazia) |

**Exemplo cURL:**
```bash
curl -X POST "http://192.168.10.51:8000/api/v1/auth/login" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"email":"operador@suaempresa.com","senha":"sua_senha"}'
```

---

### 2.2 Listar terminais ativos

Retorna os terminais de venda ativos do SAAS do operador. Exiba a lista para o operador escolher qual totem está configurando.

```
GET /operacional/terminais
Authorization: Bearer {jwt_token}
```

**Headers:**
```
Accept: application/json
Authorization: Bearer {jwt_token}
```

**Resposta 200 — sucesso:**
```json
[
  {
    "id": 1,
    "nome": "Terminal Entrada Principal",
    "codigo": "TERM-ENTRADA",
    "status": "ativo"
  },
  {
    "id": 2,
    "nome": "Terminal Balcão",
    "codigo": "TERM-BALCAO",
    "status": "ativo"
  }
]
```

| Campo | Descrição |
|---|---|
| `id` | Salvar como `terminal_id` |
| `nome` | Nome exibido na tela de seleção |
| `codigo` | Código interno do terminal |
| `status` | Sempre `"ativo"` nesta listagem |

**Respostas de erro:**

| HTTP | Body | Causa |
|---|---|---|
| `401` | `{ "erro": "Token inválido ou expirado" }` | JWT ausente, expirado ou inválido — refaça o login |

**Exemplo cURL:**
```bash
curl "http://192.168.10.51:8000/api/v1/operacional/terminais" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer {jwt_token}"
```

---

### 2.3 Validar senha do terminal → terminal token

Valida a senha operacional do terminal escolhido e retorna o `terminal_token` com escopo `totem`. **A partir desta etapa, use o `terminal_token` nas APIs do totem.**

```
POST /operacional/terminais/{terminal_id}/validar-senha
Authorization: Bearer {jwt_token}
```

**Headers:**
```
Accept: application/json
Content-Type: application/json
Authorization: Bearer {jwt_token}
```

**Body:**
```json
{
  "senha": "1234",
  "app": "totem"
}
```

| Campo | Obrigatório | Descrição |
|---|---|---|
| `senha` | ✅ | Senha operacional configurada no admin do terminal |
| `app` | ✅ | Sempre `"totem"` para o totem executável |

**Resposta 200 — sucesso:**
```json
{
  "access_token": "a3f8c2d1e9b0476f8a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3",
  "terminal": {
    "id": 1,
    "nome": "Terminal Entrada Principal",
    "codigo": "TERM-ENTRADA"
  },
  "scope": {
    "terminal_id": 1,
    "app": "totem"
  }
}
```

| Campo | Descrição |
|---|---|
| `access_token` | Salvar como `terminal_token`. **Não é JWT** — é um token opaco de 64 caracteres hex |
| `scope.terminal_id` | Deve coincidir com o `terminal_id` escolhido |
| `scope.app` | Deve ser `"totem"` |

> O token é gerado com `id_empresa` do JWT do operador. Isso é **obrigatório** para o endpoint `venda-completa` emitir cupom fiscal.

**Respostas de erro:**

| HTTP | Body | Causa |
|---|---|---|
| `401` | `{ "erro": "Senha operacional incorreta." }` | Senha digitada errada |
| `401` | `{ "erro": "Token inválido ou expirado" }` | JWT expirado — refaça login |
| `404` | `{ "message": "No query results for model..." }` | `terminal_id` inexistente ou inativo |
| `422` | `{ "message": "...", "errors": { ... } }` | `app` inválido (deve ser `totem`, `comandas` ou `chamados`) |

**Exemplo cURL:**
```bash
curl -X POST "http://192.168.10.51:8000/api/v1/operacional/terminais/1/validar-senha" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {jwt_token}" \
  -d '{"senha":"1234","app":"totem"}'
```

---

### 2.4 GET completo da configuração do terminal

Baixa ambientes, menus e produtos do terminal. Usa **versionamento** para evitar download completo quando nada mudou.

```
GET /totem/terminais/{terminal_id}/config?config_version={cv}&produtos_version={pv}
Authorization: Bearer {terminal_token}
```

**Headers:**
```
Accept: application/json
Authorization: Bearer {terminal_token}
```

**Query params:**

| Param | Obrigatório | Descrição |
|---|---|---|
| `config_version` | ❌ (padrão `0`) | Versão de config que o totem já possui |
| `produtos_version` | ❌ (padrão `0`) | Versão de produtos que o totem já possui |

Na **primeira carga**, use `config_version=0&produtos_version=0`.

**Resposta 200 — sem mudanças (`updated: false`):**
```json
{
  "updated": false,
  "config_version": 6,
  "produtos_version": 4
}
```

> Quando `updated: false`, **não há** `terminal`, `ambientes`, `menus` nem `menu_produtos`. Mantenha o cache local e apenas atualize as versões.

**Resposta 200 — com mudanças (`updated: true`):**
```json
{
  "updated": true,
  "config_version": 7,
  "produtos_version": 5,
  "terminal": {
    "id": 1,
    "nome": "Terminal Entrada Principal",
    "codigo": "TERM-ENTRADA",
    "permite_sincronizacao": true,
    "emite_cupom_fiscal": true,
    "emite_ticket": true,
    "modo_ticket": "agrupado"
  },
  "ambientes": [
    {
      "id": 1,
      "terminal_id": 1,
      "nome": "Cozinha",
      "tipo": "cozinha",
      "controla_comandas": true,
      "exibe_painel_chamados": true,
      "ativo": true,
      "ordem": 1,
      "created_at": "2026-06-01T10:00:00.000000Z",
      "updated_at": "2026-06-01T10:00:00.000000Z"
    }
  ],
  "menus": [
    {
      "id": 1,
      "terminal_id": 1,
      "ambiente_id": 1,
      "nome": "Comidas",
      "icone": "burger",
      "ativo": true,
      "ordem": 1,
      "created_at": "2026-06-01T10:00:00.000000Z",
      "updated_at": "2026-06-01T10:00:00.000000Z",
      "ambiente": {
        "id": 1,
        "terminal_id": 1,
        "nome": "Cozinha",
        "tipo": "cozinha",
        "controla_comandas": true,
        "exibe_painel_chamados": true,
        "ativo": true,
        "ordem": 1
      }
    }
  ],
  "menu_produtos": [
    {
      "id": 10,
      "menu_id": 1,
      "produto_id": 101,
      "ambiente_preparo_id": 1,
      "emite_ticket": true,
      "ordem": 1,
      "produto": {
        "id": 101,
        "nome": "X-Burguer",
        "fotos": [
          "https://cdn.exemplo.com/saas/1/produtos/101/foto1.jpg"
        ]
      }
    },
    {
      "id": 11,
      "menu_id": 1,
      "produto_id": 102,
      "ambiente_preparo_id": 1,
      "emite_ticket": true,
      "ordem": 2,
      "produto": {
        "id": 102,
        "nome": "Batata Frita G",
        "fotos": []
      }
    }
  ]
}
```

#### Campos importantes do `terminal`

| Campo | Valores | Impacto no totem |
|---|---|---|
| `emite_cupom_fiscal` | `true` / `false` | Se `true`, `venda-completa` retorna `cupom_fiscal` preenchido |
| `emite_ticket` | `true` / `false` | Se `false`, nenhum ticket é gerado |
| `modo_ticket` | `agrupado`, `por_unidade`, `nao_emitir` | Como os tickets de retirada são agrupados |
| `permite_sincronizacao` | `true` / `false` | Informativo — o totem não usa sync |

#### Montando o cardápio no totem

Para cada item em `menu_produtos`, use:

| Campo da config | Uso na venda |
|---|---|
| `id` | Referência do vínculo menu-produto |
| `menu_id` | Enviar em `itens[].menu_id` |
| `produto_id` | Enviar em `itens[].produto_id` |
| `ambiente_preparo_id` | Enviar em `itens[].ambiente_preparo_id` |
| `emite_ticket` | Enviar em `itens[].emite_ticket` |
| `produto.nome` | Exibir na tela; enviar como `itens[].nome_produto` (snapshot) |
| `produto.fotos` | URLs públicas para exibição |

> **Preço:** a config **não inclui preço**. O totem deve exibir e enviar `valor_unitario` com o preço mostrado ao cliente. O cupom fiscal usa o preço cadastrado em `ProdutoPreco` no backend (pode diferir do valor exibido se houver divergência de cadastro).

**Respostas de erro:**

| HTTP | Body | Causa |
|---|---|---|
| `401` | `{ "erro": "Token de terminal inválido ou expirado." }` | `terminal_token` inválido — refaça validação de senha |
| `403` | `{ "erro": "Token não pertence a este terminal." }` | URL usa `terminal_id` diferente do token |

**Exemplo cURL (primeira carga):**
```bash
curl "http://192.168.10.51:8000/api/v1/totem/terminais/1/config?config_version=0&produtos_version=0" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer {terminal_token}"
```

**Exemplo cURL (polling):**
```bash
curl "http://192.168.10.51:8000/api/v1/totem/terminais/1/config?config_version=7&produtos_version=5" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer {terminal_token}"
```

---

## 3. Fluxo de venda completa — `venda-completa`

Endpoint **recomendado** para finalizar a venda após pagamento aprovado pelo pinpad Fiserv.

Executa em sequência interna:
1. Calcula cupom fiscal (se `emite_cupom_fiscal: true`)
2. Cria pedido e confirma pagamento
3. Emite cupom fiscal (se aplicável)
4. Gera comandas, tickets e painel de chamados

```
POST /totem/venda-completa
Authorization: Bearer {terminal_token}
```

### Pré-requisitos

- [ ] Inicialização completa (seções 2.1 a 2.4) concluída
- [ ] Config carregada (`updated: true` pelo menos uma vez)
- [ ] Pagamento aprovado no pinpad Fiserv (antes de chamar a API)
- [ ] `idempotency_key` único gerado para esta venda

### Headers

```
Accept: application/json
Content-Type: application/json
Authorization: Bearer {terminal_token}
```

### Body completo

```json
{
  "itens": [
    {
      "produto_id": 101,
      "menu_id": 1,
      "ambiente_preparo_id": 1,
      "nome_produto": "X-Burguer",
      "quantidade": 2,
      "valor_unitario": 25.90,
      "emite_ticket": true,
      "observacao": "sem cebola"
    },
    {
      "produto_id": 102,
      "menu_id": 1,
      "ambiente_preparo_id": 1,
      "nome_produto": "Batata Frita G",
      "quantidade": 1,
      "valor_unitario": 14.00,
      "emite_ticket": true,
      "observacao": null
    }
  ],
  "pagamento": {
    "forma_pagamento": "credito",
    "gateway": "fiserv",
    "transaction_id": "TXN-FISERV-12345",
    "nsu": "000042",
    "codigo_autorizacao": "AUTH-XYZ"
  },
  "cliente_cpf": null,
  "desconto": 0,
  "acrescimo": 0,
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Campos dos itens

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `produto_id` | int\|null | ❌ | `produto_id` da config. Usado no cálculo fiscal |
| `menu_id` | int\|null | ❌ | `menu_id` da config |
| `ambiente_preparo_id` | int\|null | ❌ | `ambiente_preparo_id` da config |
| `nome_produto` | string | ✅ | Nome exibido ao cliente (snapshot histórico) |
| `quantidade` | number | ✅ | Mínimo `0.001`. Aceita decimal |
| `valor_unitario` | number | ✅ | Preço unitário no momento da venda |
| `emite_ticket` | bool | ❌ | Padrão `false`. Copiar da config |
| `observacao` | string\|null | ❌ | Máx. 500 caracteres |

#### Campos do pagamento

| Campo | Obrigatório | Valores | Descrição |
|---|---|---|---|
| `forma_pagamento` | ✅ | `pix`, `credito`, `debito`, `dinheiro` | Forma usada no pinpad |
| `gateway` | ❌ | ex: `fiserv` | Nome do gateway |
| `transaction_id` | ❌ | string | ID da transação no gateway |
| `nsu` | ❌ | string | NSU do cartão |
| `codigo_autorizacao` | ❌ | string | Código de autorização |

#### Outros campos

| Campo | Obrigatório | Descrição |
|---|---|---|
| `cliente_cpf` | ❌ | CPF do cliente para a nota (máx. 14 chars) |
| `desconto` | ❌ | Valor total de desconto em reais |
| `acrescimo` | ❌ | Valor total de acréscimo em reais |
| `idempotency_key` | ❌ (recomendado) | UUID único por venda. Máx. 100 chars |

### Resposta 201 — terminal **com** cupom fiscal

```json
{
  "pedido": {
    "id": 11,
    "codigo_senha": "002",
    "status": "em_preparo",
    "total": "65.80"
  },
  "cupom_fiscal": {
    "cupom": {
      "id_saas": 1,
      "id_empresa": 1,
      "id": 42,
      "situacao": "A",
      "numero_cupom": 42,
      "dtemissao": "2026-06-19",
      "vlr_total_produto": "65.80",
      "vlr_desconto": "0.00",
      "vlr_liquido": "65.80",
      "vlr_icms": "3.16",
      "vlr_pis": "0.43",
      "vlr_cofins": "1.98",
      "xml_path": "saas/1/empresa/1/cupons/42.xml",
      "dhinc": "2026-06-19T14:30:00.000000Z",
      "dhalt": "2026-06-19T14:30:01.000000Z",
      "dhcancelamento": null,
      "id_user_inc": 1,
      "id_user_alt": 1,
      "id_user_can": null
    },
    "empresa": {
      "id": 1,
      "razao_social": "Empresa Exemplo LTDA",
      "fantasia": "Loja Exemplo",
      "cnpj": "12345678000199",
      "ie": "123456789",
      "crt": "1"
    },
    "itens": [
      {
        "id_seq": 1,
        "id_produto": 101,
        "descproduto": "X-Burguer",
        "unidade": "UN",
        "codigo_ncm": "21069090",
        "cfop": "5102",
        "quantidade": 2,
        "vlr_unitario": 25.90,
        "vlr_desconto": 0.00,
        "vlr_total": 51.80,
        "tributos": {
          "cst_icms": "00",
          "csosn": null,
          "aliquota_icms": 4.00,
          "vlr_icms": 2.07
        }
      }
    ],
    "totais": {
      "vlr_total_produto": 65.80,
      "vlr_desconto": 0.00,
      "vlr_liquido": 65.80,
      "vlr_icms": 3.16,
      "vlr_pis": 0.43,
      "vlr_cofins": 1.98
    },
    "xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
    "xml_path": "saas/1/empresa/1/cupons/42.xml"
  }
}
```

### Resposta 201 — terminal **sem** cupom fiscal

```json
{
  "pedido": {
    "id": 11,
    "codigo_senha": "002",
    "status": "em_preparo",
    "total": "65.80"
  },
  "cupom_fiscal": null
}
```

### O que fazer com a resposta

| Campo | Ação no totem |
|---|---|
| `pedido.codigo_senha` | Exibir em destaque na tela ("Sua senha: **002**") |
| `pedido.status` | Sempre `"em_preparo"` após sucesso |
| `pedido.total` | Valor final do pedido |
| `cupom_fiscal.xml` | XML assinado — usar para impressão fiscal |
| `cupom_fiscal.cupom.numero_cupom` | Número do cupom para exibição |
| `cupom_fiscal.cupom.situacao` | `"A"` = aprovado/emitido |

### O que o backend faz após sucesso

1. Pedido criado com status `em_preparo`
2. Pagamento registrado como aprovado
3. Comandas criadas por `ambiente_preparo_id`
4. Tickets gerados para itens com `emite_ticket: true`
5. Painel de chamados atualizado
6. Evento `pedido.pago` registrado (para apps de comandas/chamados)

### Respostas de erro

| HTTP | Body | Causa | Ação no totem |
|---|---|---|---|
| `401` | `{ "erro": "Token de terminal inválido ou expirado." }` | Token expirado (30 dias) ou inválido | Refazer etapas 2.1 → 2.3 |
| `403` | `{ "erro": "Token não autorizado para esta operação." }` | Token gerado com `app` diferente de `totem` | Validar senha com `"app": "totem"` |
| `422` | `{ "erro": "Este terminal emite cupom fiscal mas o token foi gerado sem id_empresa..." }` | Token antigo sem escopo fiscal | Refazer login + validar senha |
| `422` | `{ "erro": "Produto 101 sem preço de venda cadastrado..." }` | Produto sem preço fiscal | Corrigir cadastro no admin |
| `422` | `{ "message": "...", "errors": { ... } }` | Validação de campos | Corrigir payload |
| `500` | Ver abaixo | Falha parcial na emissão fiscal | Ver cenário especial |

**Resposta 500 — pedido criado, cupom falhou:**
```json
{
  "erro": "Pedido criado mas falha ao emitir cupom fiscal: Certificado digital não encontrado",
  "pedido": {
    "id": 11,
    "codigo_senha": "002",
    "status": "em_preparo",
    "total": "65.80"
  },
  "cupom_fiscal": null
}
```

> Neste cenário o pedido **já foi criado**. Exiba o `codigo_senha` e trate a falha fiscal separadamente. **Não reenvie** com o mesmo `idempotency_key` esperando reemitir o cupom.

### Exemplo cURL

```bash
curl -X POST "http://192.168.10.51:8000/api/v1/totem/venda-completa" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {terminal_token}" \
  -d '{
    "itens": [
      {
        "produto_id": 101,
        "menu_id": 1,
        "ambiente_preparo_id": 1,
        "nome_produto": "X-Burguer",
        "quantidade": 2,
        "valor_unitario": 25.90,
        "emite_ticket": true,
        "observacao": "sem cebola"
      }
    ],
    "pagamento": {
      "forma_pagamento": "credito",
      "gateway": "fiserv",
      "transaction_id": "TXN-FISERV-12345",
      "nsu": "000042",
      "codigo_autorizacao": "AUTH-XYZ"
    },
    "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

### Idempotência

Gere um UUID **antes** de chamar a API e reutilize-o em retries de rede:

```js
const idempotencyKey = crypto.randomUUID()
```

Se a rede cair e a mesma requisição for reenviada com a mesma `idempotency_key`, o banco rejeita duplicata (constraint unique). Trate erro de duplicata exibindo o pedido original se já tiver sido criado.

---

## 4. Atualização periódica da config

O totem **não usa** o endpoint de sync (`GET /terminais/{id}/sync`). O sync é exclusivo dos painéis de comandas e chamados.

Para manter o cardápio atualizado, faça polling do config:

```
GET /totem/terminais/{terminal_id}/config?config_version={salvo}&produtos_version={salvo}
Authorization: Bearer {terminal_token}
```

| Resposta | Ação |
|---|---|
| `updated: false` | Nada mudou — manter cache local |
| `updated: true` | Substituir ambientes, menus e menu_produtos no cache |

**Intervalo recomendado:** a cada 5 minutos, ou ao retornar para a tela inicial.

---

## 5. Fluxo de venda separado (alternativo)

Mantido para compatibilidade. Exige **dois tokens** (`jwt_token` + `terminal_token`) e três chamadas separadas.

```
Pagamento aprovado pelo Fiserv
        ↓
(se emite_cupom_fiscal) POST /vendas/cupom-fiscal/calcular  [jwt_token]
        ↓
POST /totem/pedido-finalizado  [terminal_token]
        ↓
Tela mostra codigo_senha
        ↓
(se emite_cupom_fiscal) usuário clica → POST /vendas/cupom-fiscal/emitir  [jwt_token]
```

> Prefira sempre a [seção 3 — venda-completa](#3-fluxo-de-venda-completa--venda-completa).

### 5.1 Calcular cupom fiscal

```
POST /vendas/cupom-fiscal/calcular
Authorization: Bearer {jwt_token}
```

**Body:** `{ "itens": [{ "id_produto": 101, "quantidade": 2 }] }`

**Resposta 200:** `{ "cupom_id": 42, "empresa": {...}, "itens": [...], "totais": {...}, "xml": "..." }`

### 5.2 Pedido finalizado

```
POST /totem/pedido-finalizado
Authorization: Bearer {terminal_token}
```

Mesmo body da [venda-completa](#body-completo), acrescentando `cupom_fiscal_id` (ou `null`).

**Resposta 201:**
```json
{
  "pedido": {
    "id": 11,
    "codigo_senha": "002",
    "status": "em_preparo",
    "total": "65.80"
  }
}
```

### 5.3 Emitir cupom fiscal

```
POST /vendas/cupom-fiscal/emitir
Authorization: Bearer {jwt_token}
```

**Body:** `{ "cupom_id": 42 }`

**Resposta 201:** `{ "cupom": {...}, "empresa": {...}, "itens": [...], "totais": {...}, "xml": "...", "xml_path": "..." }`

---

## 6. Referência de erros HTTP

| Código | Significado | Quando ocorre |
|---|---|---|
| `200` | Sucesso (GET, calcular) | Operação concluída |
| `201` | Criado | Pedido/venda/cupom criado |
| `401` | Não autenticado | Token ausente, expirado ou senha incorreta |
| `403` | Sem permissão | Token de outro terminal ou app errado |
| `404` | Não encontrado | Terminal ou recurso inexistente |
| `422` | Validação / regra de negócio | Campos inválidos ou produto sem preço |
| `500` | Erro interno | Falha no servidor ou emissão fiscal parcial |

Formato típico de validação Laravel (`422`):
```json
{
  "message": "O campo itens é obrigatório.",
  "errors": {
    "itens": ["O campo itens é obrigatório."]
  }
}
```

Formato típico de regra de negócio (`422`):
```json
{
  "erro": "Produto 101 sem preço de venda cadastrado para a empresa 1."
}
```

---

## 7. Tokens, headers e segurança

### Headers por endpoint

| Endpoint | Authorization |
|---|---|
| `POST /auth/login` | Nenhum |
| `GET /operacional/terminais` | `Bearer {jwt_token}` |
| `POST /operacional/terminais/{id}/validar-senha` | `Bearer {jwt_token}` |
| `GET /totem/terminais/{id}/config` | `Bearer {terminal_token}` |
| `POST /totem/venda-completa` | `Bearer {terminal_token}` |
| `POST /totem/pedido-finalizado` | `Bearer {terminal_token}` |
| `POST /vendas/cupom-fiscal/calcular` | `Bearer {jwt_token}` |
| `POST /vendas/cupom-fiscal/emitir` | `Bearer {jwt_token}` |

### Expiração

| Token | Validade | Ação se expirar |
|---|---|---|
| `jwt_token` | 24h (`expira_em: 86400`) | `POST /auth/login` |
| `terminal_token` | 30 dias | `POST /operacional/terminais/{id}/validar-senha` (requer JWT válido) |

### Regras importantes

**Ticket vs Cupom Fiscal**
- **Ticket** = comprovante de retirada no balcão. Controlado por `emite_ticket` em cada item.
- **Cupom Fiscal** = documento fiscal NFC-e. Controlado por `terminal.emite_cupom_fiscal`.
- São independentes.

**Dois tokens no fluxo separado**

| Operação | Token |
|---|---|
| Calcular e emitir cupom fiscal | `jwt_token` |
| Config, venda-completa, pedido-finalizado | `terminal_token` |

No fluxo recomendado (`venda-completa`), apenas o `terminal_token` é necessário **após a inicialização**.

---

**Última atualização:** 2026-06-19
