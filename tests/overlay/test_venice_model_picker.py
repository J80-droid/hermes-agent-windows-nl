from hermes_cli.venice_model_picker import (
    apply_venice_helper_callback,
    build_venice_helper_button_rows,
    load_venice_picker_metadata,
    resolve_venice_model_for_switch,
)


def test_build_venice_helper_button_rows_includes_trait_and_openai():
    traits = {"default": "model-a"}
    mapping = {"gpt-4o": "venice-gpt"}
    rows = build_venice_helper_button_rows(traits, mapping)
    flat = [cb for row in rows for cb, _ in row]
    assert "vf:all" in flat
    assert "vf:t:0" in flat
    assert "vf:o:0" in flat


def test_apply_venice_helper_openai_preset():
    models = ["other", "venice-gpt"]
    mapping = {"gpt-4o": "venice-gpt"}
    filtered, preset = apply_venice_helper_callback("o:0", models, {}, mapping)
    assert preset == "venice-gpt"
    assert "venice-gpt" in filtered


def test_resolve_venice_model_for_switch_uses_mapping_only(monkeypatch):
    monkeypatch.setattr(
        "hermes_cli.venice_model_picker.fetch_venice_compatibility_mapping",
        lambda **kwargs: ({"gpt-4o": "zai-org-glm-5-1"}, None),
    )
    assert (
        resolve_venice_model_for_switch(
            "gpt-4o",
            api_key="key",
            base_url="https://api.venice.ai/api/v1",
        )
        == "zai-org-glm-5-1"
    )


def test_apply_venice_helper_empty_trait_filter():
    models = ["other-model"]
    traits = {"orphan": "no-match-id"}
    filtered, preset = apply_venice_helper_callback("t:0", models, traits, {})
    assert preset == "no-match-id"
    assert filtered == ["no-match-id"]


def test_load_venice_picker_metadata_requires_key():
    traits, mapping, traits_err, _ = load_venice_picker_metadata(
        api_key="", base_url="https://api.venice.ai/api/v1"
    )
    assert traits == {}
    assert mapping == {}
    assert traits_err
