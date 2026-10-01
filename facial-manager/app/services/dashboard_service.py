"""
Dashboard Service — Estatísticas (placeholder para versão local)

NOTA: Dashboard será implementado quando Supabase estiver integrado.
Para a versão local, retorna dados simulados.
"""

import logging

logger = logging.getLogger("dashboard_service")


class DashboardService:
    """Serviço de dashboard"""
    
    @staticmethod
    def get_statistics():
        """Retorna estatísticas simuladas"""
        return {
            "status": "ok",
            "message": "Dashboard será ativado com integração Supabase",
            "data": {
                "employees": 0,
                "time_records": 0,
                "occurrences": 0,
                "justifications": 0
            }
        }
