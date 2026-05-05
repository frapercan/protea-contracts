"""Tests for the ExperimentRunner ABC and result dataclasses."""

from __future__ import annotations

from typing import Any

import pytest

from protea_contracts import EvalResult, ExperimentRunner, RunResult


class _FakeRunner(ExperimentRunner):
    name = "fake"

    def fit(self, spec: dict[str, Any], dataset_uri: str, *, emit: Any) -> RunResult:
        return RunResult(model_uri="s3://fake/model.bin", metrics={"val_auc": 0.5})

    def evaluate(self, model_uri: str, eval_dataset_uri: str, *, emit: Any) -> EvalResult:
        return EvalResult(metrics={"fmax": 0.42})

    def export(self, run_id: str, output_uri: str, *, emit: Any) -> dict[str, Any]:
        return {"manifest": f"{output_uri}/manifest.json"}


class TestRunResult:
    def test_default_metrics_and_extras(self) -> None:
        r = RunResult(model_uri="s3://x")
        assert r.model_uri == "s3://x"
        assert r.metrics == {}
        assert r.extras == {}

    def test_frozen(self) -> None:
        r = RunResult(model_uri="s3://x")
        with pytest.raises((AttributeError, TypeError)):
            r.model_uri = "s3://y"  # type: ignore[misc]


class TestEvalResult:
    def test_metrics_required(self) -> None:
        e = EvalResult(metrics={"fmax": 0.5})
        assert e.metrics["fmax"] == 0.5
        assert e.extras == {}

    def test_frozen(self) -> None:
        e = EvalResult(metrics={"fmax": 0.5})
        with pytest.raises((AttributeError, TypeError)):
            e.metrics = {"fmax": 0.0}  # type: ignore[misc]


class TestExperimentRunnerContract:
    def test_subclass_must_implement_all_three(self) -> None:
        class Partial(ExperimentRunner):
            name = "partial"

            def fit(self, spec: dict[str, Any], dataset_uri: str, *, emit: Any) -> RunResult:
                return RunResult(model_uri="x")

        with pytest.raises(TypeError):
            Partial()  # type: ignore[abstract]

    def test_concrete_runner_lifecycle(self) -> None:
        r = _FakeRunner()
        run = r.fit({}, "s3://ds/", emit=lambda *a, **kw: None)
        assert isinstance(run, RunResult)
        ev = r.evaluate(run.model_uri, "s3://eval/", emit=lambda *a, **kw: None)
        assert isinstance(ev, EvalResult)
        out = r.export("run-1", "s3://out/", emit=lambda *a, **kw: None)
        assert "manifest" in out
