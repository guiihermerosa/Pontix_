"""
Instância centralizada de Jinja2Templates com filtros customizados.
Todos os routers devem importar daqui em vez de criar sua própria instância.
"""
import hashlib
from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR    = Path(__file__).resolve().parent.parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# Filtros customizados
# ---------------------------------------------------------------------------

def _fmt_dt(value, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Formata datetime Python ou string ISO para exibição."""
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.strftime(fmt)
    s = str(value).replace("T", " ")
    return s[:16] if len(s) >= 16 else s


def _fmt_bool(value) -> str:
    return "Sim" if value else "Não"


def _static_ver(path: str) -> str:
    """
    Retorna a URL do arquivo estático com hash curto como cache-bust.
    Ex: static('js/settings.js') → '/static/js/settings.js?v=a3f92b1c'
    Assim o browser sempre baixa a versão mais recente após atualizações.
    """
    full = STATIC_DIR / path.lstrip("/")
    try:
        with open(full, "rb") as f:
            h = hashlib.md5(f.read(4096)).hexdigest()[:8]
        return f"/static/{path}?v={h}"
    except FileNotFoundError:
        return f"/static/{path}"


templates.env.filters["dt"]   = _fmt_dt
templates.env.filters["bool"] = _fmt_bool
templates.env.globals["static"] = _static_ver   # {{ static('js/settings.js') }}
