from run_agent import AIAgent


class _Jatevo429(Exception):
    status_code = 429
    body = {"error": {"message": "Daily request quota exhausted"}}


def test_summarize_api_error_appends_jatevo_hint_for_429():
    agent = AIAgent(
        base_url="https://jatevo.ai/v1",
        api_key="sk-clb-test",
        provider="custom",
        model="gpt-5.5",
    )
    summary = agent.summarize_api_error(_Jatevo429("quota"))
    assert "/jquota" in summary
    assert "00:00 UTC" in summary


def test_summarize_api_error_appends_jatevo_hint_for_rate_limit_error_class():
    agent = AIAgent(
        base_url="https://jatevo.ai/v1",
        api_key="sk-clb-test",
        provider="custom",
        model="gpt-5.5",
    )

    class RateLimitError(Exception):
        pass

    summary = agent.summarize_api_error(RateLimitError("too many"))
    assert "/jquota" in summary


def test_summarize_api_error_skips_jatevo_hint_for_non_jatevo_429():
    summary = AIAgent._summarize_api_error(
        _Jatevo429("quota"),
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1",
    )
    assert "/jquota" not in summary
