"""Parser da balança Elgin/Toledo Prix. Roda com: python -m unittest tests.test_balanca -v"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import tempfile

from services import balanca_service
from services.balanca_service import aplicar_tara, interpretar_resposta


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


class TaraTest(unittest.TestCase):
    def setUp(self):
        self._orig = balanca_service._TARA_FILE
        balanca_service._TARA_FILE = Path(tempfile.mkdtemp()) / "balanca.json"

    def tearDown(self):
        balanca_service._TARA_FILE = self._orig

    def test_liquido_desconta_tara(self):
        self.assertEqual(aplicar_tara(1185, 400), 785)

    def test_prato_retirado_nao_fica_negativo(self):
        self.assertEqual(aplicar_tara(0, 400), 0)
        self.assertEqual(aplicar_tara(300, 400), 0)

    def test_sem_arquivo_tara_zero(self):
        self.assertEqual(balanca_service.obter_tara(), 0)

    def test_salva_e_le(self):
        balanca_service.salvar_tara(420)
        self.assertEqual(balanca_service.obter_tara(), 420)

    def test_rejeita_tara_invalida(self):
        for v in (-1, balanca_service.TARA_MAX_G + 1):
            with self.assertRaises(ValueError):
                balanca_service.salvar_tara(v)

    def test_arquivo_corrompido_vira_zero(self):
        balanca_service._TARA_FILE.write_text("lixo{")
        self.assertEqual(balanca_service.obter_tara(), 0)

    def test_capturar_exige_estavel_e_prato(self):
        orig = balanca_service.ler_peso
        try:
            balanca_service.ler_peso = lambda: {"status": "instavel", "peso_bruto_g": None, "estavel": False}
            with self.assertRaises(ValueError):
                balanca_service.capturar_tara()
            balanca_service.ler_peso = lambda: {"status": "ok", "peso_bruto_g": 0, "estavel": True}
            with self.assertRaises(ValueError):
                balanca_service.capturar_tara()
            balanca_service.ler_peso = lambda: {"status": "ok", "peso_bruto_g": 415, "estavel": True}
            self.assertEqual(balanca_service.capturar_tara(), 415)
            self.assertEqual(json.loads(balanca_service._TARA_FILE.read_text()), {"tara_g": 415})
        finally:
            balanca_service.ler_peso = orig


if __name__ == "__main__":
    unittest.main()
