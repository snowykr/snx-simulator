from __future__ import annotations

WORD_BITS = 16
WORD_MASK = 0xFFFF
WORD_SIGN_BIT = 0x8000
WORD_MAX_SIGNED = 0x7FFF
WORD_MIN_SIGNED = -0x8000

IMM8_BITS = 8
IMM8_MASK = 0xFF
IMM8_SIGN_BIT = 0x80
IMM8_MAX_SIGNED = 0x7F
IMM8_MIN_SIGNED = -0x80


def word(value: int) -> int:
    return value & WORD_MASK


def signed16(value: int) -> int:
    w = value & WORD_MASK
    if w >= WORD_SIGN_BIT:
        return w - (WORD_MASK + 1)
    return w


def is_negative16(value: int) -> bool:
    return (value & WORD_SIGN_BIT) != 0


def imm8(value: int) -> int:
    return value & IMM8_MASK


def signed8(value: int) -> int:
    b = value & IMM8_MASK
    if b >= IMM8_SIGN_BIT:
        return b - (IMM8_MASK + 1)
    return b


def normalize_imm8(value: int) -> int:
    return signed8(value & IMM8_MASK)
