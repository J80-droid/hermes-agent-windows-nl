from pathlib import Path

from subtitle_sidecar import filter_subtitles_indexed_via_media, subtitle_to_plain_text


def test_subtitle_to_plain_text_strips_timing(tmp_path: Path):
    vtt = tmp_path / "a.vtt"
    vtt.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nEerste zin.\n\n00:00:04.000 --> 00:00:06.000\nTweede zin.\n",
        encoding="utf-8",
    )
    text = subtitle_to_plain_text(vtt)
    assert "Eerste zin." in text
    assert "00:00:01" not in text


def test_filter_subtitles_when_media_present(tmp_path: Path):
    mp3 = tmp_path / "gesprek.mp3"
    vtt = tmp_path / "gesprek.vtt"
    mp3.write_bytes(b"\x00")
    vtt.write_text("WEBVTT\n\n1\nTekst\n", encoding="utf-8")
    kept, skipped = filter_subtitles_indexed_via_media([mp3, vtt])
    assert skipped == 1
    assert vtt not in kept
    assert mp3 in kept
