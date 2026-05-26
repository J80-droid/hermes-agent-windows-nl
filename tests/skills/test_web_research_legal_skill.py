"""Unit tests voor skills/legal/web-research-legal/scripts/web_search.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "legal"
    / "web-research-legal"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS_DIR))

import web_search as mod  # noqa: E402


GOOGLE_HTML = """
<a href="/url?q=https://wetten.nl/BWBR0005537&amp;sa=U">wet</a>
<a href="/url?q=https://uitspraken.rechtspraak.nl/id">rp</a>
<a href="/url?q=https://www.overheid.nl/doc">ov</a>
<a href="/url?q=ftp://bad.example/file">ftp</a>
"""


def _mock_urlopen(html: str):
    resp = mock.MagicMock()
    resp.read.return_value = html.encode("utf-8")
    resp.__enter__ = mock.Mock(return_value=resp)
    resp.__exit__ = mock.Mock(return_value=False)
    return resp


class TestClampMaxResults:
    @pytest.mark.parametrize(
        "value,expected",
        [(0, 10), (-1, 10), (10, 10), (99, 25)],
    )
    def test_clamps(self, value, expected):
        assert mod._clamp_max_results(value) == expected


class TestReadResponseText:
    def test_truncates_large_response(self):
        resp = mock.MagicMock()
        resp.read.return_value = b"y" * (mod.MAX_HTML_BYTES + 1)
        assert len(mod._read_response_text(resp).encode("utf-8")) <= mod.MAX_HTML_BYTES


class TestClassifyUrl:
    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://uitspraken.rechtspraak.nl/x", "rechtspraak"),
            ("https://wetten.nl/BWBR", "wet"),
            ("https://www.overheid.nl/x", "overheid"),
            ("https://zoek.officielebekendmakingen.nl/x", "overheid"),
            ("https://site.nl/jurisprudentie/x", "jurisprudentie"),
            ("https://navigator.nl/x", "juridisch_portaal"),
            ("https://legalintelligence.nl/x", "juridisch_portaal"),
            ("https://www.google.com/", "algemeen"),
            ("", "algemeen"),
        ],
    )
    def test_classification(self, url, expected):
        assert mod.classify_url(url) == expected


class TestSearchGoogle:
    @mock.patch("web_search.urllib.request.urlopen")
    @mock.patch("web_search._respect_rate_limit")
    def test_happy_path_filters_non_http(self, _rate, mock_open):
        mock_open.return_value = _mock_urlopen(GOOGLE_HTML)
        results = mod.search_google("Awb artikel", max_results=10)
        urls = [r["url"] for r in results]
        assert len(urls) == 3
        assert all(u.startswith("http") for u in urls)
        assert not any(u.startswith("ftp") for u in urls)

    @mock.patch("web_search.urllib.request.urlopen")
    @mock.patch("web_search._respect_rate_limit")
    def test_types_assigned(self, _rate, mock_open):
        mock_open.return_value = _mock_urlopen(GOOGLE_HTML)
        results = mod.search_google("q", max_results=10)
        types = {r["type"] for r in results}
        assert "wet" in types
        assert "rechtspraak" in types

    @mock.patch("web_search.urllib.request.urlopen")
    @mock.patch("web_search._respect_rate_limit")
    def test_max_results(self, _rate, mock_open):
        many = "".join(f'<a href="/url?q=https://example{i}.nl">x</a>' for i in range(30))
        mock_open.return_value = _mock_urlopen(many)
        results = mod.search_google("q", max_results=5)
        assert len(results) == 5

    @mock.patch("web_search.urllib.request.urlopen")
    @mock.patch("web_search._respect_rate_limit")
    def test_empty_html(self, _rate, mock_open):
        mock_open.return_value = _mock_urlopen("<html></html>")
        assert mod.search_google("q") == []

    @mock.patch("web_search.urllib.request.urlopen")
    @mock.patch("web_search._respect_rate_limit")
    def test_duplicate_urls_deduped(self, _rate, mock_open):
        dup = '<a href="/url?q=https://wetten.nl/x&amp;sa=U">a</a>' * 3
        mock_open.return_value = _mock_urlopen(dup)
        results = mod.search_google("q", max_results=10)
        assert len(results) == 1
        assert results[0]["url"] == "https://wetten.nl/x"

    @mock.patch("web_search.urllib.request.urlopen")
    @mock.patch("web_search._respect_rate_limit")
    def test_url_percent_decoded(self, _rate, mock_open):
        html = '<a href="/url?q=https://wetten.nl/path%20with%20spaces">x</a>'
        mock_open.return_value = _mock_urlopen(html)
        results = mod.search_google("q", max_results=5)
        assert results[0]["url"] == "https://wetten.nl/path with spaces"

    @mock.patch("web_search.urllib.request.urlopen")
    @mock.patch("web_search._respect_rate_limit")
    def test_network_error(self, _rate, mock_open):
        from urllib.error import URLError

        mock_open.side_effect = URLError("blocked")
        with pytest.raises(URLError):
            mod.search_google("q")


class TestMainCli:
    @mock.patch("web_search.search_google")
    def test_site_scope(self, mock_search, capsys):
        mock_search.return_value = [{"url": "https://wetten.nl/x", "type": "wet"}]
        with mock.patch.object(sys, "argv", ["web_search.py", "--site", "wetten.nl", "Awb"]):
            mod.main()
        called_query = mock_search.call_args[0][0]
        assert "site:wetten.nl" in called_query
        assert "[OK]" in capsys.readouterr().out

    @mock.patch("web_search.search_google")
    def test_sites_scope_or_filter(self, mock_search):
        mock_search.return_value = []
        with mock.patch.object(
            sys,
            "argv",
            ["web_search.py", "--sites", "wetten.nl,rechtspraak.nl", "test"],
        ):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 0
        q = mock_search.call_args[0][0]
        assert "site:wetten.nl" in q
        assert "site:rechtspraak.nl" in q

    @mock.patch("web_search.search_google", return_value=[])
    def test_no_results_exits_zero(self, _search, capsys):
        with mock.patch.object(sys, "argv", ["web_search.py", "niets"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 0
        assert "Geen resultaten" in capsys.readouterr().out

    @mock.patch("web_search.search_google", side_effect=OSError("net"))
    def test_search_failure_exits_one(self, _search, capsys):
        with mock.patch.object(sys, "argv", ["web_search.py", "q"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 1
        assert "failed" in capsys.readouterr().err.lower()

    def test_empty_query_exits_one(self):
        with mock.patch.object(sys, "argv", ["web_search.py", "   "]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 1

    @mock.patch("web_search.search_google", return_value=[])
    def test_max_results_clamped(self, mock_search):
        with mock.patch.object(sys, "argv", ["web_search.py", "--max", "0", "q"]):
            with pytest.raises(SystemExit):
                mod.main()
        assert mock_search.call_args[0][1] == 10

    @mock.patch("web_search.search_google")
    def test_happy_path_prints_results(self, mock_search, capsys):
        mock_search.return_value = [
            {"url": "https://wetten.nl/x", "type": "wet"},
            {"url": "https://rechtspraak.nl/y", "type": "rechtspraak"},
        ]
        with mock.patch.object(sys, "argv", ["web_search.py", "Awb"]):
            mod.main()
        out = capsys.readouterr().out
        assert "[OK] 2 resultaten" in out
        assert "[wet]" in out
        assert "[rechtspraak]" in out
