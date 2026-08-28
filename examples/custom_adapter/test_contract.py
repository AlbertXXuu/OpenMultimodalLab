"""Contract tests intended to be copied with a third-party adapter."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from openmultimodal_lab.adapters.errors import (
    AdapterInputError,
    AdapterTimeoutError,
)
from openmultimodal_lab.models import EvaluationTask

from .contract import AdapterContractError, assert_adapter_contract
from .fake_adapter import FakeBackendAdapter


class FakeBackendAdapterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.task = EvaluationTask(
            id="adapter-contract",
            prompt="Generate one stable offline response.",
        )

    def test_adapter_satisfies_contract(self) -> None:
        assert_adapter_contract(FakeBackendAdapter(), self.task)

    def test_each_required_adapter_field_is_enforced(self) -> None:
        valid = FakeBackendAdapter()
        fields = {
            "name": valid.name,
            "revision": valid.revision,
            "generate": valid.generate,
        }
        for missing_field in tuple(fields):
            with self.subTest(missing_field=missing_field):
                broken_fields = dict(fields)
                del broken_fields[missing_field]
                with self.assertRaisesRegex(
                    AdapterContractError,
                    missing_field,
                ):
                    assert_adapter_contract(
                        SimpleNamespace(**broken_fields),
                        self.task,
                    )

    def test_revision_cannot_be_reassigned_on_the_adapter(self) -> None:
        adapter = FakeBackendAdapter()
        with self.assertRaises(AttributeError):
            adapter.revision = "moving-tag"  # type: ignore[misc]

    def test_provider_input_error_maps_to_stable_status_type(self) -> None:
        invalid_task = EvaluationTask(id="empty", prompt="")
        with self.assertRaises(AdapterInputError):
            FakeBackendAdapter().generate(invalid_task)

    def test_provider_deadline_maps_to_stable_status_type(self) -> None:
        with self.assertRaises(AdapterTimeoutError):
            FakeBackendAdapter().generate(
                self.task,
                timeout_seconds=0.0001,
            )


if __name__ == "__main__":
    unittest.main()
