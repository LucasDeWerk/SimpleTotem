import { ref } from 'vue'

/**
 * Composable para usar a impressora térmica
 */
export function useThermalPrinter() {
  const printing = ref(false)
  const printError = ref(null)
  const lastPrintResult = ref(null)

  /**
   * Envia linhas de texto para a impressora
   * @param {string[]} lines - Array de strings
   * @param {object} options - { skipInit, skipCut }
   */
  async function printLines(lines, options = {}) {
    try {
      printing.value = true
      printError.value = null

      if (!window.electronAPI?.printer) {
        throw new Error('API de impressora não disponível')
      }

      const result = await window.electronAPI.printer.printLines(lines, options)
      lastPrintResult.value = result

      if (!result.success) {
        printError.value = result.message || 'Erro ao imprimir'
      }

      return result
    } catch (error) {
      printError.value = error.message
      console.error('[Printer] Erro:', error)
      return { success: false, message: error.message }
    } finally {
      printing.value = false
    }
  }

  /**
   * Envia buffer raw para a impressora
   * @param {ArrayBuffer|Uint8Array} bufferData
   */
  async function printRaw(bufferData) {
    try {
      printing.value = true
      printError.value = null

      if (!window.electronAPI?.printer) {
        throw new Error('API de impressora não disponível')
      }

      const result = await window.electronAPI.printer.printRaw(bufferData)
      lastPrintResult.value = result

      if (!result.success) {
        printError.value = result.message || 'Erro ao imprimir'
      }

      return result
    } catch (error) {
      printError.value = error.message
      console.error('[Printer] Erro:', error)
      return { success: false, message: error.message }
    } finally {
      printing.value = false
    }
  }

  /**
   * Testa a impressora
   */
  async function testPrint() {
    try {
      printing.value = true
      printError.value = null

      if (!window.electronAPI?.printer) {
        throw new Error('API de impressora não disponível')
      }

      const result = await window.electronAPI.printer.testPrint()
      lastPrintResult.value = result

      if (!result.success) {
        printError.value = result.message || 'Erro no teste de impressão'
      }

      return result
    } catch (error) {
      printError.value = error.message
      console.error('[Printer] Erro:', error)
      return { success: false, message: error.message }
    } finally {
      printing.value = false
    }
  }

  return {
    printing,
    printError,
    lastPrintResult,
    printLines,
    printRaw,
    testPrint,
  }
}
