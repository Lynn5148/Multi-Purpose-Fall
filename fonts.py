FONT_MAPS = {
    "font_sans_bold": {
        **{chr(ord('A') + i): chr(0x1D5D4 + i) for i in range(26)},
        **{chr(ord('a') + i): chr(0x1D5EE + i) for i in range(26)},
        **{chr(ord('0') + i): chr(0x1D7EC + i) for i in range(10)},
    },
    "font_sans_bold_italic": {
        **{chr(ord('A') + i): chr(0x1D63C + i) for i in range(26)},
        **{chr(ord('a') + i): chr(0x1D656 + i) for i in range(26)},
    },
    "font_sans_italic": {
        **{chr(ord('A') + i): chr(0x1D608 + i) for i in range(26)},
        **{chr(ord('a') + i): chr(0x1D622 + i) for i in range(26)},
    },
    "font_serif_bold": {
        **{chr(ord('A') + i): chr(0x1D400 + i) for i in range(26)},
        **{chr(ord('a') + i): chr(0x1D41A + i) for i in range(26)},
        **{chr(ord('0') + i): chr(0x1D7CE + i) for i in range(10)},
    },
    "font_bold_italic_serif": {
        **{chr(ord('A') + i): chr(0x1D468 + i) for i in range(26)},
        **{chr(ord('a') + i): chr(0x1D482 + i) for i in range(26)},
    },
    "font_mono": {
        **{chr(ord('A') + i): chr(0x1D670 + i) for i in range(26)},
        **{chr(ord('a') + i): chr(0x1D68A + i) for i in range(26)},
        **{chr(ord('0') + i): chr(0x1D7F6 + i) for i in range(10)},
    },
    "font_italic_serif": {
        **{chr(ord('A') + i): chr(0x1D434 + i) for i in range(26)},
        **{chr(ord('a') + i): chr(0x1D44E + i) for i in range(26)},
    },
    "font_cursive": {
        **{chr(ord('A') + i): chr(0x1D4D0 + i) for i in range(26)},
        **{chr(ord('a') + i): chr(0x1D4EA + i) for i in range(26)},
    },
    "font_fraktur": {
        **{chr(ord('A') + i): chr(0x1D504 + i) for i in range(26)},
        **{chr(ord('a') + i): chr(0x1D51E + i) for i in range(26)},
    },
    "font_gothic": {
        **{chr(ord('A') + i): chr(0x1D56C + i) for i in range(26)},
        **{chr(ord('a') + i): chr(0x1D586 + i) for i in range(26)},
    },
}

SMALL_CAPS = {
    'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ꜰ', 'g': 'ɢ',
    'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ',
    'o': 'ᴏ', 'p': 'ᴘ', 'q': 'Q', 'r': 'ʀ', 's': 'ꜱ', 't': 'ᴛ', 'u': 'ᴜ',
    'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
    'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ꜰ', 'G': 'ɢ',
    'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ',
    'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'Q', 'R': 'ʀ', 'S': 'ꜱ', 'T': 'ᴛ', 'U': 'ᴜ',
    'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
}

MIXED_CAPS = {
    'a': 'A', 'b': 'b', 'c': 'C', 'd': 'd', 'e': 'E', 'f': 'f', 'g': 'G',
    'h': 'h', 'i': 'I', 'j': 'j', 'k': 'K', 'l': 'l', 'm': 'M', 'n': 'ɴ',
    'o': 'O', 'p': 'p', 'q': 'Q', 'r': 'R', 's': 's', 't': 'T', 'u': 'u',
    'v': 'V', 'w': 'W', 'x': 'x', 'y': 'Y', 'z': 'z',
}

FULLWIDTH = {
    **{chr(ord('A') + i): chr(0xFF21 + i) for i in range(26)},
    **{chr(ord('a') + i): chr(0xFF41 + i) for i in range(26)},
    **{chr(ord('0') + i): chr(0xFF10 + i) for i in range(10)},
    ' ': '　',
}

SUPERSCRIPT = {
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ', 'f': 'ᶠ', 'g': 'ᵍ',
    'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ', 'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ',
    'o': 'ᵒ', 'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ', 'v': 'ᵛ',
    'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
    'A': 'ᴬ', 'B': 'ᴮ', 'D': 'ᴰ', 'E': 'ᴱ', 'G': 'ᴳ', 'H': 'ᴴ', 'I': 'ᴵ',
    'J': 'ᴶ', 'K': 'ᴷ', 'L': 'ᴸ', 'M': 'ᴹ', 'N': 'ᴺ', 'O': 'ᴼ', 'P': 'ᴾ',
    'R': 'ᴿ', 'T': 'ᵀ', 'U': 'ᵁ', 'V': 'ⱽ', 'W': 'ᵂ',
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
}

BLOCK = {
    'A': '🅐', 'B': '🅑', 'C': '🅒', 'D': '🅓', 'E': '🅔', 'F': '🅕', 'G': '🅖',
    'H': '🅗', 'I': '🅘', 'J': '🅙', 'K': '🅚', 'L': '🅛', 'M': '🅜', 'N': '🅝',
    'O': '🅞', 'P': '🅟', 'Q': '🅠', 'R': '🅡', 'S': '🅢', 'T': '🅣', 'U': '🅤',
    'V': '🅥', 'W': '🅦', 'X': '🅧', 'Y': '🅨', 'Z': '🅩',
    'a': '🅐', 'b': '🅑', 'c': '🅒', 'd': '🅓', 'e': '🅔', 'f': '🅕', 'g': '🅖',
    'h': '🅗', 'i': '🅘', 'j': '🅙', 'k': '🅚', 'l': '🅛', 'm': '🅜', 'n': '🅝',
    'o': '🅞', 'p': '🅟', 'q': '🅠', 'r': '🅡', 's': '🅢', 't': '🅣', 'u': '🅤',
    'v': '🅥', 'w': '🅦', 'x': '🅧', 'y': '🅨', 'z': '🅩',
}


def convert_font(text: str, font_key: str) -> str:
    if font_key == "font_small_caps":
        return ''.join(SMALL_CAPS.get(c, c) for c in text)
    elif font_key == "font_mixed_caps":
        return ''.join(MIXED_CAPS.get(c, c) for c in text)
    elif font_key == "font_fullwidth":
        return ''.join(FULLWIDTH.get(c, c) for c in text)
    elif font_key == "font_superscript":
        return ''.join(SUPERSCRIPT.get(c, c) for c in text)
    elif font_key == "font_block":
        return ''.join(BLOCK.get(c, c) for c in text)
    elif font_key in FONT_MAPS:
        return ''.join(FONT_MAPS[font_key].get(c, c) for c in text)
    return text
