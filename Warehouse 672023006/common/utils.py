import bleach
import re

def sanitize_input(text, max_length=255):
    if not text:
        return ""
    # Strip HTML tags
    cleaned = bleach.clean(str(text), tags=[], attributes={}, protocols=[])
    # Remove special chars
    cleaned = re.sub(r'[<>\'\";&]', '', cleaned)
    return cleaned[:max_length]

def validate_id(id_str):
    if not id_str or not isinstance(id_str, str):
        return False
    return bool(re.match(r'^[0-9a-fA-F]{24}$', id_str))

def sanitize_text(s, maxlen=255):
    if not s:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = s.strip()
    # remove suspicious chars (basic). For richer sanitization use bleach.
    s = re.sub(r"[\x00-\x1f<>]", "", s)
    return s[:maxlen]

def to_int(v, default=None):
    try:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return default
        return int(v)
    except Exception:
        return default