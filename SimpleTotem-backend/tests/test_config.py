"""Testes para as validações de configuração SiTef sensíveis à homologação
Fiserv: faixa reservada de SITEF_ID_TERMINAL, e não-vazio para
SITEF_CNPJ_AUTOMACAO / SITEF_ID_LOJA.

Os CNPJs de exemplo do roteiro (12523654185985 / 31406434895111) e a loja
"00000000" são intencionalmente ACEITOS — o suporte técnico da Fiserv
confirmou por escrito que são os dados fictícios oficiais de pré-homologação,
apesar do texto do roteiro sugerir o contrário. Ver comentário em
core/config.py antes de reintroduzir qualquer rejeição desses valores.

Roda sem pytest: python -m unittest tests.test_config -v
(ou python tests/test_config.py diretamente)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import _validar_nao_vazio, _validar_id_terminal  # noqa: E402


class TestValidarIdTerminal(unittest.TestCase):
    def test_id_normal_passa(self):
        _validar_id_terminal("ST000001")  # não deve levantar

    def test_faixa_proibida_meio(self):
        with self.assertRaises(RuntimeError):
            _validar_id_terminal("SE000950")

    def test_faixa_proibida_limite_inferior(self):
        with self.assertRaises(RuntimeError):
            _validar_id_terminal("SE000900")

    def test_faixa_proibida_limite_superior(self):
        with self.assertRaises(RuntimeError):
            _validar_id_terminal("SE000999")

    def test_fora_da_faixa_abaixo(self):
        _validar_id_terminal("SE000899")  # não deve levantar

    def test_fora_da_faixa_acima(self):
        _validar_id_terminal("SE001000")  # não deve levantar


class TestValidarNaoVazio(unittest.TestCase):
    def test_valor_vazio_rejeitado(self):
        with self.assertRaises(RuntimeError):
            _validar_nao_vazio("SITEF_CNPJ_AUTOMACAO", "")

    def test_valor_so_espacos_rejeitado(self):
        with self.assertRaises(RuntimeError):
            _validar_nao_vazio("SITEF_ID_LOJA", "   ")

    def test_cnpj_exemplo_automacao_aceito(self):
        # Confirmado por escrito pelo suporte Fiserv: dado fictício oficial do
        # roteiro de pré-homologação — não deve ser rejeitado.
        _validar_nao_vazio("SITEF_CNPJ_AUTOMACAO", "12523654185985")

    def test_cnpj_exemplo_estabelecimento_aceito(self):
        _validar_nao_vazio("SITEF_ID_LOJA", "31406434895111")

    def test_id_loja_zeros_aceito(self):
        # Confirmado por escrito pelo suporte Fiserv como loja oficial de testes.
        _validar_nao_vazio("SITEF_ID_LOJA", "00000000")

    def test_cnpj_real_passa(self):
        _validar_nao_vazio("SITEF_CNPJ_AUTOMACAO", "05071869000140")  # não deve levantar


if __name__ == "__main__":
    unittest.main()
