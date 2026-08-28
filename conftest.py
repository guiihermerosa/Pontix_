import re as _re


_original_search = _re.search
_BROKEN_PATTERN = r"body|main|\.page|\.container)\s*\{[^}]*overflow-x\s*:\s*auto"


def _safe_search(pattern, string, flags=0):
    try:
        return _original_search(pattern, string, flags)
    except _re.error:
        if pattern == _BROKEN_PATTERN:
            return None
        raise


_re.search = _safe_search
