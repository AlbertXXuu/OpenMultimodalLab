# Third-party adapter tutorial

This guide closes one concrete contributor gap: `CONTRIBUTING.md` required a
minimal example and contract test for new backends, but the repository did not
provide an executable third-party implementation. The example stays outside the
built-in backend factory so it demonstrates the public Python boundary without
adding a supported model or dependency.

## Run the offline example

From a fresh checkout, create an environment and install the dependency-free
core package:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m examples.custom_adapter.run_example
.\.venv\Scripts\python.exe -m unittest examples.custom_adapter.test_contract -v
```

On Linux or macOS, replace `.\.venv\Scripts\python.exe` with
`.venv/bin/python`. Both commands use the fake backend in
[`examples/custom_adapter/`](../../examples/custom_adapter/) and make no
network request, load no model, and require no credential.

The run command passes `FakeBackendAdapter` to the real benchmark runner and
prints a successful record containing a content-addressed revision and JSON-safe
usage metadata. The contract command runs five tests. One test removes `name`,
`revision`, and `generate` in turn and proves that each incomplete adapter is
rejected.

## Contract to implement

An adapter receives one validated
[`EvaluationTask`](../../src/openmultimodal_lab/models.py) and returns one
[`ModelOutput`](../../src/openmultimodal_lab/models.py). It does not load the
dataset, score an answer, write a report, or read `expected_keywords` to produce
an answer.

| Surface | Requirement | Why it is evidence-critical |
| --- | --- | --- |
| `name` | Stable, non-empty backend identifier | Joins run records and manifests. |
| `revision` | Immutable model or provider revision, preferably a commit or content hash | Prevents a moving alias from silently changing the evaluated system. |
| `generate(task, *, timeout_seconds=None)` | Synchronous call returning `ModelOutput` | Lets the runner apply one timing and failure boundary. |
| `ModelOutput.text` | Generated string | Supplies the response that the evaluator scores. |
| `ModelOutput.backend` | Exactly the adapter `name` | Prevents identity drift inside a run. |
| `ModelOutput.model_revision` | Exactly the adapter `revision` | Binds every output to the evaluated revision. |
| `ModelOutput.usage` | JSON-safe metadata without secrets or personal paths | Preserves provider settings and measurements for later audit. |

The copyable
[`assert_adapter_contract`](../../examples/custom_adapter/contract.py) checks
that shape, identity agreement, and repeated deterministic output under one
fixed task and revision. A stochastic backend should freeze its supported seed
and decoding settings for an evaluation run; if the provider cannot do that,
record the stochastic configuration and repetitions instead of weakening the
test silently.

## Map provider failures before they reach the runner

Catch narrow provider exceptions and raise the matching typed adapter error:

| Provider condition | OpenMultimodalLab error | Recorded status |
| --- | --- | --- |
| Unsupported or rejected task input | `AdapterInputError` | `invalid_task` |
| Missing optional SDK/runtime | `AdapterDependencyError` | `model_load_error` |
| Model initialization failure | `ModelLoadError` | `model_load_error` |
| Accelerator memory exhaustion | `AdapterOutOfMemoryError` | `out_of_memory` |
| Cooperative deadline exceeded | `AdapterTimeoutError` | `timeout` |

Unknown exceptions are retained as `generation_error`. Do not convert every
exception to one generic provider error: that would erase whether a retry is
meaningful. The fake client and adapter in
[`fake_adapter.py`](../../examples/custom_adapter/fake_adapter.py) demonstrate
input and deadline translation without simulating a real model.

## Replace the fake client

Keep the `FakeBackendAdapter` shape and replace only the client call and output
normalization. Before proposing a built-in backend, add:

1. an immutable upstream model revision and license link;
2. exact optional dependencies and a bounded hardware statement;
3. deterministic generation settings or a registered repetition protocol;
4. JSON-safe usage metadata needed to reproduce the call;
5. positive output tests and one test per mapped provider failure;
6. one real command executed from a clean environment.

Third-party code can pass an adapter directly to `run_benchmark`; editing the
built-in CLI factory is a separate maintenance decision and requires evidence
that repository users need that backend to be supported here.
