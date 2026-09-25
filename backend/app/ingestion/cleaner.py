import re
import unicodedata


_BROKEN_IDENTIFIER_PATTERN = re.compile(
    r"\b([A-Z]{2,}|ERR|ERROR|FW|HTTP|IP|WAN|LAN|WIFI|WI-FI|DNS)\s*\n\s*([A-Z0-9_.-]+)\b"
)
_BROKEN_NUMBER_PATTERN = re.compile(r"\b([A-Z]{2,}|ERR|ERROR|FW|HTTP)\s*\n\s*(\d+[A-Z0-9_.-]*)\b")
_HYPHENATED_LINE_BREAK_PATTERN = re.compile(r"(?<=[A-Za-z0-9])-\n(?=[A-Za-z0-9])")
_SOFT_LINE_BREAK_PATTERN = re.compile(r"(?<=[a-z0-9,;:])\n(?=[a-z0-9(])")


def clean_text(text: str) -> str:
    text = normalize_line_endings(text)
    text = remove_control_characters(text)
    text = repair_hyphenated_line_breaks(text)
    text = repair_broken_technical_identifiers(text)
    text = repair_soft_line_breaks(text)
    text = normalize_whitespace(text)
    text = collapse_repeated_blank_lines(text)
    return text.strip()


def normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def remove_control_characters(text: str) -> str:
    allowed = {"\n", "\t"}
    characters: list[str] = []
    for character in text:
        if character in allowed:
            characters.append(character)
        elif unicodedata.category(character)[0] == "C":
            characters.append(" ")
        else:
            characters.append(character)
    return "".join(characters)


def repair_hyphenated_line_breaks(text: str) -> str:
    return _HYPHENATED_LINE_BREAK_PATTERN.sub("", text)


def repair_broken_technical_identifiers(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = _BROKEN_IDENTIFIER_PATTERN.sub(r"\1 \2", text)
        text = _BROKEN_NUMBER_PATTERN.sub(r"\1 \2", text)
    return text


def repair_soft_line_breaks(text: str) -> str:
    return _SOFT_LINE_BREAK_PATTERN.sub(" ", text)


def normalize_whitespace(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line)
    return "\n".join(lines)


def collapse_repeated_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text)
