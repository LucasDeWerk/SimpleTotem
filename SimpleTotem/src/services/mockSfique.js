// ─── Dados mockados da API SimplesFique ────────────────────────────────────────
//
// O totem não depende mais de nenhum servidor externo (SimplesFique). Toda a
// lógica de login em 3 passos, catálogo e registro de pedido continua igual —
// apenas os dados voltam daqui em vez de uma chamada de rede real.
//
// A única integração externa real que permanece é o pinpad/CliSiTef (Fiserv),
// tratada pelo backend local em services/sitef_*.

function uid(prefix = 'mock') {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export const MOCK_EMPRESA = {
  id_saas: 1,
  id_empresa: 1,
  id: 1,
  razao_social: 'SimpleTotem Demonstração Ltda',
  nome_fantasia: 'SimpleTotem Demo',
  cpf_cnpj: '12345678000190',
  endereco: 'Av. Homologação',
  numero: '1000',
  cep: '01310100',
  cidade: 'São Paulo',
  id_uf: 'SP',
  bairro: 'Centro',
}

const MOCK_TERMINAIS = [
  { id: 1, nome: 'Totem Homologação 01', codigo: 'T01' },
]

const MOCK_AMBIENTES = [
  { id: 1, nome: 'Cozinha' },
  { id: 2, nome: 'Bar' },
]

const MOCK_MENUS = [
  { id: 1, nome: 'Lanches', ordem: 1, ativo: true, icone: '' },
  { id: 2, nome: 'Bebidas', ordem: 2, ativo: true, icone: '' },
  { id: 3, nome: 'Sobremesas', ordem: 3, ativo: true, icone: '' },
  { id: 4, nome: 'Combos', ordem: 4, ativo: true, icone: '' },
]

const MOCK_MENU_PRODUTOS = [
  { id: 1, produto_id: 1, menu_id: 1, nome_produto: 'X-Burger Clássico', preco: 24.9, emite_ticket: true, ambiente_preparo_id: 1 },
  { id: 2, produto_id: 2, menu_id: 1, nome_produto: 'X-Bacon', preco: 27.9, emite_ticket: true, ambiente_preparo_id: 1 },
  { id: 3, produto_id: 3, menu_id: 1, nome_produto: 'Batata Frita Média', preco: 14.9, emite_ticket: true, ambiente_preparo_id: 1 },
  { id: 4, produto_id: 4, menu_id: 4, nome_produto: 'Combo X-Burger + Batata + Refri', preco: 34.9, emite_ticket: true, ambiente_preparo_id: 1 },
  { id: 5, produto_id: 5, menu_id: 2, nome_produto: 'Coca-Cola Lata 350ml', preco: 6.5, emite_ticket: false, ambiente_preparo_id: null },
  { id: 6, produto_id: 6, menu_id: 2, nome_produto: 'Guaraná Lata 350ml', preco: 6.5, emite_ticket: false, ambiente_preparo_id: null },
  { id: 7, produto_id: 7, menu_id: 2, nome_produto: 'Água Mineral 500ml', preco: 4.0, emite_ticket: false, ambiente_preparo_id: null },
  { id: 8, produto_id: 8, menu_id: 2, nome_produto: 'Suco Natural de Laranja 300ml', preco: 8.9, emite_ticket: true, ambiente_preparo_id: 2 },
  { id: 9, produto_id: 9, menu_id: 3, nome_produto: 'Sorvete Casquinha', preco: 9.9, emite_ticket: true, ambiente_preparo_id: 1 },
  { id: 10, produto_id: 10, menu_id: 3, nome_produto: 'Petit Gateau', preco: 16.9, emite_ticket: true, ambiente_preparo_id: 1 },
]

// Senha de retirada sequencial — o registro completo da venda (para o painel
// de cancelamento) vive no backend, em dados/vendas_homologacao.json.
let proximaSenha = 100

export async function mockLogin(email) {
  await sleep(250)
  return {
    token: uid('jwt'),
    empresa: MOCK_EMPRESA,
    empresas: [MOCK_EMPRESA],
    saas: { id_saas: 1, nome: 'SimpleTotem Demo SaaS' },
    usuario: { email, nome: (email.split('@')[0] || 'Operador') },
  }
}

export async function mockListarTerminais() {
  await sleep(200)
  return MOCK_TERMINAIS
}

export async function mockValidarSenha(terminalId) {
  await sleep(200)
  const terminal = MOCK_TERMINAIS.find(t => t.id === Number(terminalId)) || MOCK_TERMINAIS[0]
  return {
    access_token: uid('terminal'),
    terminal: { ...terminal, emite_cupom_fiscal: false },
  }
}

export async function mockObterConfig() {
  await sleep(200)
  return {
    updated: true,
    config_version: 1,
    produtos_version: 1,
    ambientes: MOCK_AMBIENTES,
    menus: MOCK_MENUS,
    menu_produtos: MOCK_MENU_PRODUTOS,
    terminal: { ...MOCK_TERMINAIS[0], emite_cupom_fiscal: false },
  }
}

export async function mockEmitirCupom() {
  await sleep(300)
  return { emitido: true }
}

export async function mockVendaCompleta() {
  await sleep(300)
  const codigoSenha = String(proximaSenha++)
  return {
    pedido: { codigo_senha: codigoSenha },
    cupom_fiscal: null,
  }
}

export async function mockListarTiposPagamento() {
  await sleep(150)
  return [
    { id: '3', descricao: 'Cartão de Crédito' },
    { id: '4', descricao: 'Cartão de Débito' },
    { id: '17', descricao: 'PIX' },
  ]
}
