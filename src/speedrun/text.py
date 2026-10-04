"""Decode game text as the bridge writes it (contract C5).

The bridge writes ASCII JSON in which every game-text byte >= 0x80 is a
``\\u00XX`` escape of that byte, so a parsed string holds one Latin-1 code
point per game byte. MI1's charset follows the DOS code-page layout (cp437),
not Mac Roman ("Mêlée" is stored as ``M\\x88l\\x82e``), and draws 0x0F as a
trademark sign.

The compiler does not use this: it compares object names from
``objects.json`` and ``steps.toml`` raw, one code point per game byte.
"""

_TRADEMARK = 0x0F


def decode_game_text(value: object) -> object:
    """Turn bridge text (one code point per game byte) into readable Unicode.

    Anything that cannot have come from the bridge (a non-string, or a code
    point above 0xFF) is returned unchanged rather than raising.
    """
    if not isinstance(value, str):
        return value
    try:
        raw = value.encode("latin-1")
    except UnicodeEncodeError:
        return value
    return raw.decode("cp437").replace(chr(_TRADEMARK), "™")
