from app.ingestion.cleaner import clean_text


def test_clean_text_repairs_broken_error_codes() -> None:
    text = "If you see ERROR\n105, restart the router."

    assert "ERROR 105" in clean_text(text)


def test_clean_text_preserves_exact_identifiers() -> None:
    text = "Use ERR_105, FW_2.3.17, AX4200, and 192.168.0.1."

    cleaned = clean_text(text)

    assert "ERR_105" in cleaned
    assert "FW_2.3.17" in cleaned
    assert "AX4200" in cleaned
    assert "192.168.0.1" in cleaned


def test_clean_text_preserves_numbered_procedures() -> None:
    text = """
    1. Open the router admin page.
    2. Select System.
    3. Click Backup / Flash Firmware.
    """

    cleaned = clean_text(text)

    assert "1. Open the router admin page." in cleaned
    assert "2. Select System." in cleaned
    assert "3. Click Backup / Flash Firmware." in cleaned


def test_clean_text_repairs_hyphenated_line_breaks() -> None:
    text = "Trouble-\nshooting steps"

    assert "Troubleshooting steps" in clean_text(text)


def test_clean_text_removes_control_characters() -> None:
    text = "Reset\x00 the router\x08 now"

    assert clean_text(text) == "Reset the router now"


def test_clean_text_collapses_excess_blank_lines() -> None:
    text = "Line one\n\n\n\nLine two"

    assert clean_text(text) == "Line one\n\nLine two"
