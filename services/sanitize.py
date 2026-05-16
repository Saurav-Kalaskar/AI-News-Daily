"""
Strict MarkdownV2 sanitizer for Telegram messages.
Imperative: escape every character in the Telegram MarkdownV2 reserved set.
"""
import re

# Characters that must be escaped in Telegram MarkdownV2 parse_mode
_RESERVED: str = r"_\*\[\]\(\)~`>#\+\-=\|{}\.\!"

# Pre-compiled regex for unpaired special chars
_RE_UNPAIRED_STAR = re.compile(r"(?<!\*)\*(?!\*)")
_RE_UNPAIRED_UNDERSCORE = re.compile(r"(?<!_)_(?!_)")
_RE_UNPAIRED_BACKTICK = re.compile(r"(?<!`)`(?!`)")
_RE_UNPAIRED_BRACKET_LEFT = re.compile(r"\[(?![^\]]+\])")
_RE_UNPAIRED_BRACKET_RIGHT = re.compile(r"(?<!\])\]")


def sanitize_markdown(text: str) -> str:
    """
    Sanitize a string for Telegram MarkdownV2 parse_mode.
    Escapes all unpaired and reserved characters.
    Preserves normal letters, numbers, and newlines.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")
    # Escape unpaired special characters that form markdown pairs
    text = _RE_UNPAIRED_STAR.sub(r"\\*", text)
    text = _RE_UNPAIRED_UNDERSCORE.sub(r"\\_", text)
    text = _RE_UNPAIRED_BACKTICK.sub(r"\\`", text)
    # Escape unpaired brackets when not part of a markdown link [text](url)
    text = _RE_UNPAIRED_BRACKET_LEFT.sub(r"\\[", text)
    text = _RE_UNPAIRED_BRACKET_RIGHT.sub(r"\\]", text)
    # Escape all other reserved MarkdownV2 characters
    escaped = []
    for ch in text:
        if ch in _RESERVED:
            escaped.append(f"\\{ch}")
        else:
            escaped.append(ch)
    return "".join(escaped).strip()
