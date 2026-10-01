"""
Portal Routes - FUTURE: Integração com Supabase

NOTA: Portal será ativado quando Supabase estiver integrado.
Por enquanto, mantém compatibilidade.
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger("routes_portal")

router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


@router.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}
