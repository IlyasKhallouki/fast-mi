"""Unit tests for the shared game-text decoder (contract C5).

The bridge writes ASCII JSON in which a game byte >= 0x80 is the escape
``\\u00XX``, so a decoded JSON string holds one Latin-1 code point per game
byte. MI1's charset follows the DOS code-page layout (cp437), with 0x0F
drawn as a trademark sign.
"""

import pytest

from speedrun.text import decode_game_text


@pytest.mark.parametrize(
    ("raw", "text"),
    [
        ("M\u0088l\u0082e", "Mêlée"),  # stored as M\x88l\x82e (room-030-store/local-211.txt [0110])
        ("Grog\u000f", "Grog™"),
        ("\u0080a ira", "Ça ira"),
        ("plain ASCII", "plain ASCII"),
        ("", ""),
    ],
)
def test_decodes_cp437_bytes(raw, text):
    assert decode_game_text(raw) == text


def test_is_not_mac_roman():
    # In Mac Roman 0x88 is "à" and 0x82 is "Ç".
    assert decode_game_text("\u0088\u0082") == "êé"


def test_code_points_above_ff_are_kept_as_is():
    # Cannot have come from the bridge's byte escaping: keep the text rather than fail.
    assert decode_game_text("already ’ decoded") == "already ’ decoded"


@pytest.mark.parametrize("value", [None, 3, ["x"]])
def test_non_strings_pass_through(value):
    assert decode_game_text(value) == value
