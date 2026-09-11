"""The SEPARATION_MODEL licence gate: no torch needed, the check runs before any import."""

from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

from app.config import Settings, override_settings
from app.pipeline import separation
from app.pipeline.separation import (
    SEPARATION_MODELS,
    SeparationModelLicenceError,
    check_model_licence,
    ensure_licensed,
    model_info,
)
from worker.common import load_pipeline

HTDEMUCS_MESSAGE = (
    "SEPARATION_MODEL 'htdemucs' weights are not licensed for commercial use; set "
    "SEPARATION_MODEL to a licensed model or ALLOW_UNLICENSED_SEPARATION_MODEL=1 for "
    "internal testing"
)


def test_table_records_research_only_demucs_weights() -> None:
    for name in ("htdemucs", "htdemucs_ft", "htdemucs_6s"):
        row = SEPARATION_MODELS[name]
        assert row["family"] == separation.FAMILY_DEMUCS
        assert row["commercial_use"] is False and "research" in row["weights_licence"]
    assert all(
        set(row) == {"family", "weights_licence", "commercial_use"}
        for row in SEPARATION_MODELS.values()
    )
    assert model_info("mdx_extra") == {
        "family": separation.FAMILY_DEMUCS,
        "weights_licence": "unknown",
        "commercial_use": None,
    }
    assert model_info("htdemucs") is not SEPARATION_MODELS["htdemucs"]  # a copy


@pytest.mark.parametrize("env", ["development", "test", "staging"])
def test_any_model_outside_production(env: str) -> None:
    assert check_model_licence("htdemucs", env)["commercial_use"] is False
    assert check_model_licence("mdx_extra", env)["commercial_use"] is None


def test_production_refuses_research_weights_with_the_documented_message() -> None:
    with pytest.raises(SeparationModelLicenceError) as info:
        check_model_licence("htdemucs", "production")
    assert str(info.value) == HTDEMUCS_MESSAGE
    for name in ("htdemucs_ft", "htdemucs_6s"):
        with pytest.raises(SeparationModelLicenceError, match="not licensed for commercial use"):
            check_model_licence(name, "production")


def test_production_refuses_unknown_weights() -> None:
    with pytest.raises(SeparationModelLicenceError, match="have no recorded licence"):
        check_model_licence("mdx_extra", "production")


def test_production_allows_licensed_or_explicitly_overridden(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setitem(
        SEPARATION_MODELS,
        "licensed_roformer",
        {"family": separation.FAMILY_ROFORMER, "weights_licence": "MIT", "commercial_use": True},
    )
    assert check_model_licence("licensed_roformer", "production")["family"] == "roformer"
    with caplog.at_level(logging.WARNING, logger="tonamorph.pipeline.separation"):
        info = check_model_licence("htdemucs", "production", allow_unlicensed=True)
    assert info["commercial_use"] is False
    assert any("ALLOW_UNLICENSED_SEPARATION_MODEL" in r.message for r in caplog.records)


@pytest.mark.parametrize(
    ("raw", "allowed"), [("1", True), ("true", True), ("0", False), ("", False)]
)
def test_ensure_licensed_reads_the_override_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, raw: str, allowed: bool
) -> None:
    monkeypatch.setenv("ALLOW_UNLICENSED_SEPARATION_MODEL", raw)
    settings = Settings.model_construct(env="production", separation_model="htdemucs")
    if allowed:
        assert ensure_licensed(settings)["family"] == "demucs"
    else:
        with pytest.raises(SeparationModelLicenceError):
            ensure_licensed(settings)


def test_settings_validate_the_model_name() -> None:
    assert Settings(_env_file=None).separation_model == "htdemucs"
    padded = Settings(_env_file=None, separation_model=" htdemucs_ft ")
    assert padded.separation_model == "htdemucs_ft"
    for bad in ("", "../weights", "name with spaces", "-leading"):
        with pytest.raises(ValidationError, match="SEPARATION_MODEL"):
            Settings(_env_file=None, separation_model=bad)


def test_worker_refuses_local_pipeline_in_production_before_importing_torch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALLOW_UNLICENSED_SEPARATION_MODEL", raising=False)
    settings = Settings.model_construct(
        env="production", separation_model="htdemucs", tonamorph_pipeline="local"
    )
    with pytest.raises(SeparationModelLicenceError, match="not licensed for commercial use"):
        load_pipeline(settings)
    with override_settings(settings), pytest.raises(SeparationModelLicenceError):
        separation.load_model()


def test_worker_gate_only_applies_to_the_in_process_gpu_pipeline() -> None:
    from app.pipeline import fake

    settings = Settings.model_construct(
        env="production", separation_model="htdemucs", tonamorph_pipeline="fake"
    )
    assert load_pipeline(settings) is fake.run_pipeline
