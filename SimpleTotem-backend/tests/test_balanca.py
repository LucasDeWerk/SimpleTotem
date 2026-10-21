"""Parser da balança Elgin/Toledo Prix. Roda com: python -m unittest tests.test_balanca -v"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.balanca_service import interpretar_resposta


class InterpretarRespostaTest(unittest.TestCase):
    def test_peso_em_gramas(self):
        self.assertEqual(interpretar_resposta(b"\x0200225\x03"), {"status": "ok", "peso_g": 225})

    def test_zero(self):
        self.assertEqual(interpretar_resposta(b"\x0200000\x03"), {"status": "ok", "peso_g": 0})

    def test_instavel(self):
        self.assertEqual(interpretar_resposta(b"\x02IIIII\x03"), {"status": "instavel", "peso_g": None})

    def test_ignora_lixo_antes_do_frame(self):
        self.assertEqual(interpretar_resposta(b"\x03\x03\x03\x0200165\x03")["peso_g"], 165)

    def test_so_lixo_e_invalido(self):
        self.assertEqual(interpretar_resposta(b"\x03" * 16)["status"], "invalido")

    def test_vazio_sem_resposta(self):
        self.assertEqual(interpretar_resposta(b"")["status"], "sem_resposta")


if __name__ == "__main__":
    unittest.main()
