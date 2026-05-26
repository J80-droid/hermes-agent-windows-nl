"""Unit tests voor skills/legal/rechtspraak-zoeken/scripts/search_rechtspraak.py."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest import mock

import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "legal"
    / "rechtspraak-zoeken"
    / "scripts"
)
sys.path.insert(0, str(SCRIPTS_DIR))

import search_rechtspraak as mod  # noqa: E402


DDG_HTML = """
<a class="result__a" href="https://uitspraken.rechtspraak.nl/ECLI:NL:RVS:2019:899">Uitspraak RVS</a>
<span class="result__snippet">Artikel 7:10 Awb termijn</span>
<a class="result__a" href="https://example.com/no-ecli">Overig</a>
"""

GOOGLE_HTML = """
<a href="/url?q=https://deeplink.rechtspraak.nl/uitspraak?id=ECLI:NL:HR:2024:123&amp;sa=U">link</a>
<a href="/url?q=javascript:void(0)">skip</a>
"""


def _mock_urlopen(html: str):
    """Context manager mock voor urllib.request.urlopen."""
    resp = mock.MagicMock()
    resp.read.return_value = html.encode("utf-8")
    resp.__enter__ = mock.Mock(return_value=resp)
    resp.__exit__ = mock.Mock(return_value=False)
    return resp


class TestExtractEcli:
    def test_happy_path_rvs(self):
        assert mod.extract_ecli("https://uitspraken.rechtspraak.nl/ECLI:NL:RVS:2019:899") == "ECLI:NL:RVS:2019:899"

    def test_deeplink_query_param(self):
        url = "https://deeplink.rechtspraak.nl/uitspraak?id=ECLI:NL:HR:2024:123"
        assert mod.extract_ecli(url) == "ECLI:NL:HR:2024:123"

    def test_ecli_in_plain_text(self):
        assert mod.extract_ecli("Zie ECLI:NL:CRVB:2020:456 voor details.") == "ECLI:NL:CRVB:2020:456"

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "geen ecli",
            "https://example.com/page",
            "ECLI:NL:INVALID",
            "ecli:nl:rvs:2019:899",  # lowercase — pattern is uppercase
        ],
    )
    def test_no_match_returns_none(self, text):
        assert mod.extract_ecli(text) is None


class TestSearchDuckduckgo:
    @mock.patch("search_rechtspraak.urllib.request.urlopen")
    @mock.patch("search_rechtspraak._respect_rate_limit")
    def test_happy_path_parses_results(self, _rate, mock_open):
        mock_open.return_value = _mock_urlopen(DDG_HTML)
        results = mod.search_duckduckgo("Awb bezwaar", site="rechtspraak.nl", max_results=5)
        assert len(results) == 2
        assert results[0]["engine"] == "duckduckgo"
        assert "rechtspraak.nl" in results[0]["url"]
        assert results[0]["snippet"] == "Artikel 7:10 Awb termijn"
        mock_open.assert_called_once()

    @mock.patch("search_rechtspraak.urllib.request.urlopen")
    @mock.patch("search_rechtspraak._respect_rate_limit")
    def test_site_prefix_added_to_query(self, _rate, mock_open):
        mock_open.return_value = _mock_urlopen("")
        mod.search_duckduckgo("test", site="rechtspraak.nl", max_results=1)
        req = mock_open.call_args[0][0]
        url = getattr(req, "full_url", str(req))
        assert "site%3Arechtspraak.nl" in url or "site:rechtspraak.nl" in url

    @mock.patch("search_rechtspraak.urllib.request.urlopen")
    @mock.patch("search_rechtspraak._respect_rate_limit")
    def test_no_site_skips_prefix(self, _rate, mock_open):
        mock_open.return_value = _mock_urlopen(DDG_HTML)
        mod.search_duckduckgo("test", site=None, max_results=1)
        req = mock_open.call_args[0][0]
        url = getattr(req, "full_url", str(req))
        assert "site:" not in url or "site:None" not in url

    @mock.patch("search_rechtspraak.urllib.request.urlopen")
    @mock.patch("search_rechtspraak._respect_rate_limit")
    def test_empty_html_returns_empty_list(self, _rate, mock_open):
        mock_open.return_value = _mock_urlopen("<html></html>")
        assert mod.search_duckduckgo("query") == []

    @mock.patch("search_rechtspraak.urllib.request.urlopen")
    @mock.patch("search_rechtspraak._respect_rate_limit")
    def test_max_results_respected(self, _rate, mock_open):
        many = "".join(
            f'<a class="result__a" href="https://x{i}.nl">T{i}</a>' for i in range(20)
        )
        mock_open.return_value = _mock_urlopen(many)
        results = mod.search_duckduckgo("q", max_results=3)
        assert len(results) == 3

    @mock.patch("search_rechtspraak.urllib.request.urlopen", side_effect=OSError("network down"))
    @mock.patch("search_rechtspraak._respect_rate_limit")
    def test_network_error_propagates(self, _rate, _open):
        with pytest.raises(OSError, match="network down"):
            mod.search_duckduckgo("query")

    @mock.patch("search_rechtspraak.urllib.request.urlopen")
    @mock.patch("search_rechtspraak._respect_rate_limit")
    def test_snippet_html_stripped(self, _rate, mock_open):
        html_page = '<a class="result__a" href="https://a.nl">T</a><span class="result__snippet"><b>bold</b> text</span>'
        mock_open.return_value = _mock_urlopen(html_page)
        results = mod.search_duckduckgo("q", max_results=1)
        assert results[0]["snippet"] == "bold text"


class TestSearchGoogle:
    @mock.patch("search_rechtspraak.urllib.request.urlopen")
    @mock.patch("search_rechtspraak._respect_rate_limit")
    def test_happy_path_extracts_urls(self, _rate, mock_open):
        mock_open.return_value = _mock_urlopen(GOOGLE_HTML)
        results = mod.search_google("Awb", max_results=5)
        assert len(results) == 1
        assert results[0]["engine"] == "google"
        assert "ECLI:NL:HR:2024:123" in results[0]["url"]

    @mock.patch("search_rechtspraak.urllib.request.urlopen")
    @mock.patch("search_rechtspraak._respect_rate_limit")
    def test_non_http_urls_filtered(self, _rate, mock_open):
        html_page = '<a href="/url?q=javascript:alert(1)">x</a>'
        mock_open.return_value = _mock_urlopen(html_page)
        assert mod.search_google("q") == []

    @mock.patch("search_rechtspraak.urllib.request.urlopen", side_effect=TimeoutError())
    @mock.patch("search_rechtspraak._respect_rate_limit")
    def test_timeout_propagates(self, _rate, _open):
        with pytest.raises(TimeoutError):
            mod.search_google("query")


class TestFormatResults:
    def test_prints_ecli_when_present(self, capsys):
        mod.format_results(
            [
                {
                    "title": "Uitspraak",
                    "url": "https://uitspraken.rechtspraak.nl/ECLI:NL:RVS:2019:899",
                    "snippet": "snippet",
                    "engine": "duckduckgo",
                }
            ]
        )
        out = capsys.readouterr().out
        assert "ECLI:NL:RVS:2019:899" in out
        assert "snippet" in out

    def test_empty_results_no_output(self, capsys):
        mod.format_results([])
        assert capsys.readouterr().out == ""

    def test_title_fallback_to_url(self, capsys):
        mod.format_results([{"title": "", "url": "https://only-url.nl", "snippet": "", "engine": "google"}])
        assert "https://only-url.nl" in capsys.readouterr().out


class TestRespectRateLimit:
    @mock.patch("search_rechtspraak.time.sleep")
    @mock.patch("search_rechtspraak.time.time", side_effect=[100.0, 101.0])
    def test_sleeps_when_called_too_soon(self, mock_time, mock_sleep):
        mod._last_req_time = 99.0
        mod._respect_rate_limit()
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] > 0

    @mock.patch("search_rechtspraak.time.sleep")
    @mock.patch("search_rechtspraak.time.time", return_value=200.0)
    def test_no_sleep_when_enough_elapsed(self, _time, mock_sleep):
        mod._last_req_time = 0.0
        mod._respect_rate_limit()
        mock_sleep.assert_not_called()


class TestMainCli:
    @mock.patch("search_rechtspraak.format_results")
    @mock.patch("search_rechtspraak.search_google")
    @mock.patch("search_rechtspraak.search_duckduckgo")
    def test_google_only_flag(self, mock_ddg, mock_google, mock_fmt, capsys):
        mock_google.return_value = [{"title": "t", "url": "https://a.nl", "snippet": "", "engine": "google"}]
        with mock.patch.object(sys, "argv", ["search_rechtspraak.py", "--google", "Awb"]):
            mod.main()
        mock_ddg.assert_not_called()
        mock_google.assert_called_once()
        mock_fmt.assert_called_once()
        assert "Google search" in capsys.readouterr().out

    @mock.patch("search_rechtspraak.search_google")
    @mock.patch(
        "search_rechtspraak.search_duckduckgo",
        side_effect=RuntimeError("ddg fail"),
    )
    def test_ddg_failure_falls_back_to_google(self, mock_ddg, mock_google, capsys):
        mock_google.return_value = [{"title": "", "url": "https://b.nl", "snippet": "", "engine": "google"}]
        with mock.patch.object(sys, "argv", ["search_rechtspraak.py", "query"]):
            mod.main()
        out = capsys.readouterr().out
        assert "Falling back" in out
        mock_google.assert_called_once()

    @mock.patch("search_rechtspraak.search_duckduckgo", return_value=[])
    def test_no_results_exits_zero(self, _ddg, capsys):
        with mock.patch.object(sys, "argv", ["search_rechtspraak.py", "niets"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 0
        assert "Geen resultaten" in capsys.readouterr().out

    @mock.patch("search_rechtspraak.search_google", side_effect=OSError("fail"))
    def test_google_only_failure_exits_one(self, _google):
        with mock.patch.object(sys, "argv", ["search_rechtspraak.py", "--google", "q"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 1

    @mock.patch("search_rechtspraak.search_duckduckgo", side_effect=RuntimeError("ddg"))
    @mock.patch("search_rechtspraak.search_google", side_effect=RuntimeError("google"))
    def test_both_engines_fail_exits_one(self, _ddg, _google, capsys):
        with mock.patch.object(sys, "argv", ["search_rechtspraak.py", "q"]):
            with pytest.raises(SystemExit) as exc:
                mod.main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "Google fallback also failed" in combined
