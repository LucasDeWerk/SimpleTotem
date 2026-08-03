"""Testes para a validação de SITEF_ID_TERMINAL (faixa reservada Fiserv).

Roda sem pytest: python -m unittest tests.test_config -v
(ou python tests/test_config.py diretamente)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import _validar_id_terminal  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
