/**
 * Imagens em /imagens na raiz do repositório, nomeadas pelo id do produto (ex.: 12.jpeg).
 */
const imageModules = import.meta.glob(
  '../../../imagens/*.{jpeg,jpg,png,webp,JPEG,JPG,PNG,WEBP}',
  { eager: true, query: '?url', import: 'default' }
)

const imageByProductId = new Map()

for (const path of Object.keys(imageModules)) {
  const fileName = path.split('/').pop() || ''
  const idMatch = fileName.match(/^(\d+)\./)
  if (idMatch) {
    imageByProductId.set(Number(idMatch[1]), imageModules[path])
  }
}

/** URL da imagem local pelo id_produto; senão usa foto vinda da API. */
export function getProductImageUrl(idProduto, apiFoto = '') {
  if (idProduto == null || idProduto === '') return apiFoto || ''
  const id = Number(idProduto)
  if (!Number.isFinite(id)) return apiFoto || ''
  return imageByProductId.get(id) || apiFoto || ''
}
