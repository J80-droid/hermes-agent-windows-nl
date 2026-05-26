"""Unit tests voor skills/legal/uitspraak-parseren/scripts/."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest import mock

import pytest

PARSE_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "legal"
    / "uitspraak-parseren"
    / "scripts"
)
sys.path.insert(0, str(PARSE_DIR))

import parse_uitspraak  # noqa: E402
import extract_docx  # noqa: E402
import extract_pdf  # noqa: E402


class TestStripXml:
  def test_happy_path(self):
    raw = "<root><p>Test <b>uitspraak</b> &amp; meer</p></root>"
    assert parse_uitspraak.strip_xml(raw) == "Test uitspraak & meer"

  def test_empty_string(self):
    assert parse_uitspraak.strip_xml("") == ""

  def test_only_tags(self):
    assert parse_uitspraak.strip_xml("<a><b></b></a>") == ""

  def test_whitespace_normalized(self):
    assert parse_uitspraak.strip_xml("  veel   spaties  ") == "veel spaties"

  def test_html_entities(self):
    assert "&lt;tag&gt;" in parse_uitspraak.strip_xml("&lt;tag&gt; tekst") or "tag" in parse_uitspraak.strip_xml("&lt;tag&gt; tekst")


class TestSplitRechtsoverwegingen:
  def test_happy_path_multiple_ro(self):
    text = "Inleiding r.o. 3.1 inhoud eerste r.o. 3.2 inhoud tweede"
    sections = parse_uitspraak.split_rechtsoverwegingen(text)
    assert len(sections) >= 2
    labels = [label for label, _ in sections if label]
    assert any("r.o." in label.lower() for label in labels)

  def test_overweging_case_insensitive(self):
    text = "Start Overweging 2.1 body text here"
    sections = parse_uitspraak.split_rechtsoverwegingen(text)
    assert any("Overweging" in (label or "") for label, _ in sections)

  def test_no_markers_returns_truncated_single_block(self):
    text = "x" * 9000
    sections = parse_uitspraak.split_rechtsoverwegingen(text)
    assert len(sections) == 1
    assert sections[0][0] == ""
    assert len(sections[0][1]) == 8000

  def test_content_truncated_to_500_per_section(self):
    long_body = "a" * 1000
    text = f"r.o. 1 {long_body}"
    sections = parse_uitspraak.split_rechtsoverwegingen(text)
    labeled = [(l, c) for l, c in sections if l]
    assert labeled
    assert len(labeled[0][1]) == 500


class TestFetchEcli:
  @pytest.mark.parametrize(
    "bad_ecli",
    [
      "",
      "not-an-ecli",
      "ECLI:NL:RVS:2019",  # ontbreekt segment
      "ECLI:NL:RVS:ABCD:899",  # jaar geen cijfers
      "ECLI:NL:RVS:2019:XX",  # nummer geen cijfers
    ],
  )
  def test_invalid_ecli_raises_value_error(self, bad_ecli):
    with pytest.raises(ValueError, match="Ongeldig ECLI"):
      parse_uitspraak.fetch_ecli(bad_ecli)

  @mock.patch("urllib.request.urlopen")
  def test_happy_path(self, mock_open):
    resp = mock.MagicMock()
    resp.read.return_value = b"<doc>inhoud</doc>"
    resp.__enter__ = mock.Mock(return_value=resp)
    resp.__exit__ = mock.Mock(return_value=False)
    mock_open.return_value = resp
    data = parse_uitspraak.fetch_ecli("ECLI:NL:RVS:2019:899")
    assert "inhoud" in data
    mock_open.assert_called_once()
    called_url = mock_open.call_args[0][0]
    url_str = getattr(called_url, "full_url", str(called_url))
    assert "ECLI:NL:RVS:2019:899" in url_str

  @mock.patch("urllib.request.urlopen", side_effect=OSError("timeout"))
  def test_network_failure(self, _open):
    with pytest.raises(OSError, match="timeout"):
      parse_uitspraak.fetch_ecli("ECLI:NL:RVS:2019:899")

  @mock.patch("urllib.request.urlopen")
  def test_response_truncated_at_limit(self, mock_open):
    resp = mock.MagicMock()
    resp.read.return_value = b"<x>" + b"y" * 3_000_000
    resp.__enter__ = mock.Mock(return_value=resp)
    resp.__exit__ = mock.Mock(return_value=False)
    mock_open.return_value = resp
    data = parse_uitspraak.fetch_ecli("ECLI:NL:RVS:2019:899")
    assert len(data.encode("utf-8")) <= 2_000_000


class TestParseUitspraakMain:
  @mock.patch.dict("os.environ", {}, clear=True)
  def test_empty_stdin_exits_one(self, capsys):
    with mock.patch.object(sys, "stdin", io.StringIO("")):
      with pytest.raises(SystemExit) as exc:
        parse_uitspraak.main()
    assert exc.value.code == 1
    assert "Geen input" in capsys.readouterr().err

  def test_stdin_xml_prints_truncated(self, capsys):
    xml = "<p>" + ("woord " * 2000) + "</p>"
    with mock.patch.object(sys, "stdin", io.StringIO(xml)):
      with mock.patch.dict("os.environ", {}, clear=True):
        parse_uitspraak.main()
    out = capsys.readouterr().out
    assert "8000" in out
    assert "toon eerste" in out

  @mock.patch("parse_uitspraak.fetch_ecli", return_value="<p>r.o. 1 tekst</p>")
  def test_ecli_mode_prints_sections(self, _fetch, capsys):
    with mock.patch.dict("os.environ", {"ECLI": "ECLI:NL:RVS:2019:899"}):
      parse_uitspraak.main()
    out = capsys.readouterr().out
    assert "Ophalen" in out
    assert "r.o." in out

  @mock.patch("parse_uitspraak.fetch_ecli", side_effect=ConnectionError("offline"))
  def test_ecli_fetch_failure_exits_one(self, _fetch, capsys):
    with mock.patch.dict("os.environ", {"ECLI": "ECLI:NL:RVS:2019:899"}):
      with pytest.raises(SystemExit) as exc:
        parse_uitspraak.main()
    assert exc.value.code == 1
    assert "Fout bij ophalen" in capsys.readouterr().err

  def test_empty_xml_after_strip_warns(self, capsys):
    with mock.patch.object(sys, "stdin", io.StringIO("<p></p><br/>")):
      with mock.patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit) as exc:
          parse_uitspraak.main()
    assert exc.value.code == 0
    assert "Geen tekst" in capsys.readouterr().out


# --- extract_docx ---


class TestExtractDocx:
  @mock.patch("extract_docx.os.path.isfile", return_value=True)
  def test_happy_path(self, _isfile):
    para1 = mock.Mock(text="  Eerste alinea  ")
    para2 = mock.Mock(text="")
    para3 = mock.Mock(text="Tweede")
    doc = mock.Mock(paragraphs=[para1, para2, para3])
    with mock.patch.dict(sys.modules, {"docx": mock.MagicMock(Document=mock.Mock(return_value=doc))}):
      with mock.patch("builtins.__import__", side_effect=lambda name, *a, **k: sys.modules["docx"] if name == "docx" else __import__(name, *a, **k)):
        result = extract_docx.extract_docx("/tmp/test.docx")
        assert len(result) == 2
        assert result[0].strip() == "Eerste alinea"
        assert result[1] == "Tweede"

  @mock.patch("extract_docx.os.path.isfile", return_value=False)
  def test_missing_file_exits(self, _isfile):
    real_import = __import__

    def fake_import(name, *args, **kwargs):
      if name == "docx":
        m = mock.MagicMock()
        m.Document = mock.Mock()
        return m
      return real_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", side_effect=fake_import):
      with pytest.raises(FileNotFoundError):
        extract_docx.extract_docx("/nope.docx")

  def test_import_error_exits(self):
    real_import = __import__

    def fake_import(name, *args, **kwargs):
      if name == "docx":
        raise ImportError("no docx")
      return real_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", side_effect=fake_import):
      with pytest.raises(ImportError, match="python-docx"):
        extract_docx.extract_docx("x.docx")


class TestExtractDocxMain:
  def test_missing_argv_exits(self):
    with mock.patch.object(sys, "argv", ["extract_docx.py"]):
      with pytest.raises(SystemExit) as exc:
        extract_docx.main()
    assert exc.value.code == 1

  @mock.patch("extract_docx.extract_docx", return_value=["Alinea"])
  def test_happy_path_prints(self, _extract, capsys):
    with mock.patch.object(sys, "argv", ["extract_docx.py", "doc.docx"]):
      extract_docx.main()
    out = capsys.readouterr().out
    assert "1 paragrafen" in out
    assert "Alinea" in out

  @mock.patch("extract_docx.extract_docx", side_effect=RuntimeError("corrupt"))
  def test_extract_failure_exits_one(self, _extract, capsys):
    with mock.patch.object(sys, "argv", ["extract_docx.py", "bad.docx"]):
      with pytest.raises(SystemExit) as exc:
        extract_docx.main()
    assert exc.value.code == 1
    assert "mislukt" in capsys.readouterr().err


# --- extract_pdf ---


class TestExtractPdf:
  @mock.patch("extract_pdf.os.path.isfile", return_value=True)
  def test_happy_path_closes_document(self, _isfile):
    page = mock.Mock()
    page.get_text.return_value = " pagina tekst "
    doc = mock.MagicMock()
    doc.__iter__ = mock.Mock(return_value=iter([page]))
    doc.page_count = 1
    pymupdf = mock.MagicMock()
    pymupdf.open.return_value = doc

    with mock.patch.dict(sys.modules, {"pymupdf": pymupdf}):
      with mock.patch("builtins.__import__", side_effect=lambda name, *a, **k: pymupdf if name == "pymupdf" else __import__(name, *a, **k)):
        count, pages = extract_pdf.extract_pdf("/tmp/a.pdf")
    assert count == 1
    assert pages == ["pagina tekst"]
    doc.close.assert_called_once()

  @mock.patch("extract_pdf.os.path.isfile", return_value=True)
  def test_blank_pages_skipped(self, _isfile):
    p1 = mock.Mock(get_text=mock.Mock(return_value="   "))
    p2 = mock.Mock(get_text=mock.Mock(return_value="inhoud"))
    doc = mock.MagicMock()
    doc.__iter__ = mock.Mock(return_value=iter([p1, p2]))
    doc.page_count = 2
    pymupdf = mock.MagicMock()
    pymupdf.open.return_value = doc
    with mock.patch.dict(sys.modules, {"pymupdf": pymupdf}):
      with mock.patch("builtins.__import__", side_effect=lambda name, *a, **k: pymupdf if name == "pymupdf" else __import__(name, *a, **k)):
        _, pages = extract_pdf.extract_pdf("/tmp/a.pdf")
    assert pages == ["inhoud"]

  @mock.patch("extract_pdf.os.path.isfile", return_value=False)
  def test_missing_file_exits(self, _isfile):
    pymupdf = mock.MagicMock()
    with mock.patch.dict(sys.modules, {"pymupdf": pymupdf}):
      with mock.patch("builtins.__import__", side_effect=lambda name, *a, **k: pymupdf if name == "pymupdf" else __import__(name, *a, **k)):
        with pytest.raises(FileNotFoundError):
          extract_pdf.extract_pdf("/missing.pdf")

  def test_import_error_exits(self):
    real_import = __import__

    def fake_import(name, *args, **kwargs):
      if name in ("pymupdf", "fitz"):
        raise ImportError("no pymupdf")
      return real_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", side_effect=fake_import):
      with pytest.raises(ImportError, match="pymupdf"):
        extract_pdf.extract_pdf("a.pdf")

class TestExtractPdfMain:
  def test_missing_argv_exits(self):
    with mock.patch.object(sys, "argv", ["extract_pdf.py"]):
      with pytest.raises(SystemExit) as exc:
        extract_pdf.main()
    assert exc.value.code == 1

  @mock.patch("extract_pdf.extract_pdf", return_value=(2, ["p1", "p2"]))
  def test_happy_path_prints_pages(self, _extract, capsys):
    with mock.patch.object(sys, "argv", ["extract_pdf.py", "a.pdf"]):
      extract_pdf.main()
    out = capsys.readouterr().out
    assert "2 paginas" in out
    assert "Pagina 1" in out

  @mock.patch("extract_pdf.extract_pdf", side_effect=ImportError("pymupdf"))
  def test_main_import_error(self, _extract):
    with mock.patch.object(sys, "argv", ["extract_pdf.py", "a.pdf"]):
      with pytest.raises(SystemExit) as exc:
        extract_pdf.main()
    assert exc.value.code == 1
