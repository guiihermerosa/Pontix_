"""
API Routes — Gerenciamento de Ocorrências (FUTURE: Supabase Integration)

NOTA: Este módulo será ativado quando Supabase estiver totalmente integrado.
Por enquanto, mantém placeholders para não quebrar imports no main.py

Para versão local, use:
- /api/v1/accountant/companies/{company_id}/occurrences (já implementado)
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger("routes_occurrences")

router = APIRouter(prefix="/api/v1/occurrences", tags=["occurrences"])


@router.get("/{company_id}")
async def list_occurrences(company_id: str):
    """Placeholder - Ocorrências com Supabase em desenvolvimento"""
    return {
        "success": True,
        "data": [],
        "message": "Endpoint será ativado com integração Supabase",
        "info": "Use /api/v1/accountant/companies/{company_id}/occurrences para versão local"
    }


@router.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}
