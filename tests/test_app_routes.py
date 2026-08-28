import importlib
import unittest
from unittest.mock import patch


def _load_app_module():
    import notificacoes

    with patch.object(notificacoes, "iniciar_em_segundo_plano", lambda: None):
        app_module = importlib.import_module("app")
        return importlib.reload(app_module)


class AppRouteTests(unittest.TestCase):
    def test_gerar_rota_repassa_filtros_personalizados(self):
        app_module = _load_app_module()
        capturado = {}

        def fake_iniciar(inicio, fim, nome_periodo, **kwargs):
            capturado["inicio"] = inicio
            capturado["fim"] = fim
            capturado["nome_periodo"] = nome_periodo
            capturado["kwargs"] = kwargs
            return "capturado"

        with patch.object(app_module, "_iniciar_geracao_relatorio", fake_iniciar):
            client = app_module.app.test_client()
            resposta = client.post(
                "/gerar",
                data={
                    "tipo": "personalizado",
                    "periodo_inicio": "2026-08-01",
                    "periodo_fim": "2026-08-15",
                    "matricula": "12345",
                    "nome": "Alice",
                    "departamento": "TI",
                    "turno": "Manha",
                },
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data, b"capturado")
        self.assertEqual(capturado["nome_periodo"], "Personalizado")
        self.assertEqual(capturado["kwargs"]["filtros"]["matricula"], "12345")
        self.assertEqual(capturado["kwargs"]["filtros"]["nome"], "Alice")
        self.assertEqual(capturado["kwargs"]["filtros"]["departamento"], "TI")
        self.assertEqual(capturado["kwargs"]["filtros"]["turno"], "Manha")
        self.assertEqual(capturado["inicio"].isoformat(), "2026-08-01")
        self.assertEqual(capturado["fim"].isoformat(), "2026-08-15")

    def test_gerar_rota_mantem_fluxos_existentes(self):
        app_module = _load_app_module()
        casos = [
            ("semana", "Semanal", (2026, 8, 3), (2026, 8, 9)),
            ("mes", "Mensal", (2026, 7, 1), (2026, 7, 31)),
            ("semana_atual", "SemanaAtual", (2026, 8, 10), (2026, 8, 17)),
            ("mes_atual", "MesAtual", (2026, 8, 1), (2026, 8, 17)),
        ]

        for tipo, nome_periodo, inicio_a, fim_a in casos:
            capturado = {}

            def fake_iniciar(inicio, fim, nome_periodo_recebido, **kwargs):
                capturado["inicio"] = inicio
                capturado["fim"] = fim
                capturado["nome_periodo"] = nome_periodo_recebido
                capturado["kwargs"] = kwargs
                return "capturado"

            with patch.object(app_module.ponto_core, "periodo_semana_passada", lambda: (app_module.ponto_core.date(*inicio_a), app_module.ponto_core.date(*fim_a))), \
                 patch.object(app_module.ponto_core, "periodo_mes_passado", lambda: (app_module.ponto_core.date(*inicio_a), app_module.ponto_core.date(*fim_a))), \
                 patch.object(app_module.ponto_core, "periodo_semana_atual", lambda: (app_module.ponto_core.date(*inicio_a), app_module.ponto_core.date(*fim_a))), \
                 patch.object(app_module.ponto_core, "periodo_mes_atual", lambda: (app_module.ponto_core.date(*inicio_a), app_module.ponto_core.date(*fim_a))), \
                 patch.object(app_module, "_iniciar_geracao_relatorio", fake_iniciar):
                client = app_module.app.test_client()
                resposta = client.post("/gerar", data={"tipo": tipo, "matricula": "12345"})

            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(capturado["nome_periodo"], nome_periodo)
            self.assertEqual(capturado["kwargs"]["filtros"]["matricula"], "12345")


if __name__ == "__main__":
    unittest.main()
