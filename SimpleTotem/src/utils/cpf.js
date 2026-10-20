export function somenteDigitos(valor) {
  return String(valor || '').replace(/\D/g, '')
}

export function cpfValido(valor) {
  const d = somenteDigitos(valor)
  if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false
  for (const n of [9, 10]) {
    let soma = 0
    for (let i = 0; i < n; i++) soma += Number(d[i]) * (n + 1 - i)
    const dv = ((soma * 10) % 11) % 10
    if (dv !== Number(d[n])) return false
  }
  return true
}

export function formatarCpf(valor) {
  const d = somenteDigitos(valor).slice(0, 11)
  return d
    .replace(/^(\d{3})(\d)/, '$1.$2')
    .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1-$2')
}
