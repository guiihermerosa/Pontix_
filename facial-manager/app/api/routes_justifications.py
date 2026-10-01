"""
API Routes — Gerenciamento de Justificativas (FUTURE: Supabase Integration)

NOTA: Este módulo será ativado quando Supabase estiver totalmente integrado.
Por enquanto, mantém placeholders para não quebrar imports no main.py

Para versão local, use:
- /api/v1/accountant/companies/{company_id}/justifications (já implementado)
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger("routes_justifications")

router = APIRouter(prefix="/api/v1/justifications", tags=["justifications"])


@router.get("/{company_id}")
async def list_justifications(company_id: str):
    """Placeholder - Justificativas com Supabase em desenvolvimento"""
    return {
        "success": True,
        "data": [],
        "message": "Endpoint será ativado com integração Supabase",
        "info": "Use /api/v1/accountant/companies/{company_id}/justifications para versão local"
    }


@router.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}
