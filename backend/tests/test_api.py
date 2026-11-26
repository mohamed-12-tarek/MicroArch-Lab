"""API tests — the 9 checks from ``01_M1.md`` plus the contract details.

Owner: M1.  Run with::

    cd backend
    pytest tests/test_api.py -v

The two "golden" cycle-count tests need M5's runner.  Until
``core/pipeline.py`` exports ``run_simulation`` they are skipped instead of
failing, and the placeholder path is tested instead.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.api import service
from app.core.errors import MAX_FILE_SIZE_BYTES
from app.schemas.simulation import SimulationResponse

MOCKS_DIR = Path(__file__).resolve().parents[2] / "frontend" / "src" / "mocks"
MOCK_FILES = [
    "simulate-success.json",
    "simulate-load-use.json",
    "simulate-memory.json",
    "simulate-error.json",
]

RUNNER_READY = service.engine_name() == "real"
requires_runner = pytest.mark.skipif(
    not RUNNER_READY, reason="M5's run_simulation is not merged yet"
)
requires_mock = pytest.mark.skipif(
    RUNNER_READY, reason="The real engine is connected, no placeholder to check"
)

SIMPLE_PROGRAM = "ADDI R1, R0, 10\nADDI R2, R0, 20\nADD R3, R1, R2\n"


def _simulate(client, code: str) -> dict:
    response = client.post("/api/simulate", json={"code": code})
    assert response.status_code == 200, response.text
    return response.json()


def _upload(client, filename: str, content: bytes):
    return client.post(
        "/api/simulate/upload",
        files={"file": (filename, content, "application/octet-stream")},
    )


# ---------------------------------------------------------------------------
# 1. /api/health
# ---------------------------------------------------------------------------
def test_health_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["engine"] in {"real", "mock"}


def test_root_points_at_docs(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


# ---------------------------------------------------------------------------
# 2. Valid code -> success: true
# ---------------------------------------------------------------------------
def test_simulate_valid_code_returns_success(client):
    body = _simulate(client, SIMPLE_PROGRAM)

    assert body["success"] is True
    assert body["total_cycles"] >= 1
    assert body["errors"] == []
    assert [item["text"] for item in body["instructions"]] == [
        "ADDI R1, R0, 10",
        "ADDI R2, R0, 20",
        "ADD R3, R1, R2",
    ]
    assert len(body["history"]) == body["total_cycles"]


def test_simulate_returns_32_registers_and_final_state(client):
    body = _simulate(client, SIMPLE_PROGRAM)

    registers = body["history"][0]["registers"]
    assert len(registers) == 32
    assert set(registers) == {f"R{i}" for i in range(32)}
    assert body["final_state"]["registers"]["R0"] == 0


def test_cycle_numbers_are_sequential(client):
    body = _simulate(client, SIMPLE_PROGRAM)
    assert [cycle["cycle"] for cycle in body["history"]] == list(
        range(1, body["total_cycles"] + 1)
    )


# ---------------------------------------------------------------------------
# 3. Unknown instruction -> success: false, correct line
# ---------------------------------------------------------------------------
def test_simulate_unsupported_instruction_reports_line(client):
    body = _simulate(client, "ADDI R1, R0, 5\nMULT R2, R1, R1\n")

    assert body["success"] is False
    assert body["total_cycles"] == 0
    assert body["history"] == []
    assert body["errors"] == [
        {"line": 2, "message": "Unsupported instruction: MULT", "type": "parse"}
    ]


def test_parse_errors_still_use_http_200(client):
    response = client.post("/api/simulate", json={"code": "MULT R1, R2, R3"})
    assert response.status_code == 200
    assert response.json()["success"] is False


def test_every_parse_error_is_reported(client):
    code = "MULT R1, R2, R3\nADD R1, R2\nADD R32, R1, R2\n"
    body = _simulate(client, code)

    assert body["success"] is False
    assert [error["line"] for error in body["errors"]] == [1, 2, 3]
    assert body["errors"][2]["message"] == "Invalid register: R32"


def test_empty_program_is_reported(client):
    body = _simulate(client, "# only a comment\n\n")

    assert body["success"] is False
    assert body["errors"] == [
        {"line": None, "message": "Program is empty", "type": "parse"}
    ]


# ---------------------------------------------------------------------------
# 4. Missing body -> 422
# ---------------------------------------------------------------------------
def test_simulate_without_code_returns_422(client):
    response = client.post("/api/simulate", json={})
    assert response.status_code == 422


def test_simulate_with_wrong_type_returns_422(client):
    response = client.post("/api/simulate", json={"code": 123})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 5-7. File upload
# ---------------------------------------------------------------------------
def test_upload_asm_file_succeeds(client, example_code):
    content = example_code("basic.asm").encode("utf-8")
    response = _upload(client, "basic.asm", content)

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_upload_accepts_uppercase_extension(client):
    response = _upload(client, "BASIC.ASM", SIMPLE_PROGRAM.encode("utf-8"))
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_upload_rejects_txt_file(client):
    response = _upload(client, "program.txt", SIMPLE_PROGRAM.encode("utf-8"))

    assert response.status_code == 400
    body = response.json()
    assert body["type"] == "request"
    assert "Unsupported file type" in body["detail"]


def test_upload_rejects_file_without_extension(client):
    response = _upload(client, "program", SIMPLE_PROGRAM.encode("utf-8"))
    assert response.status_code == 400


def test_upload_rejects_too_large_file(client):
    content = b"ADDI R1, R0, 1\n" + b"#" * MAX_FILE_SIZE_BYTES
    response = _upload(client, "huge.asm", content)

    assert response.status_code == 413
    assert response.json()["type"] == "request"


def test_upload_accepts_exactly_100kb(client):
    head = b"ADDI R1, R0, 1\n"
    content = head + b"#" * (MAX_FILE_SIZE_BYTES - len(head) - 1) + b"\n"
    assert len(content) == MAX_FILE_SIZE_BYTES

    response = _upload(client, "limit.asm", content)
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_upload_requires_a_file(client):
    response = client.post("/api/simulate/upload")
    assert response.status_code == 422


def test_upload_accepts_utf8_bom(client):
    content = "\ufeffADDI R1, R0, 7\n".encode("utf-8")
    response = _upload(client, "bom.asm", content)

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_upload_rejects_binary_file(client):
    response = _upload(client, "binary.asm", b"\xff\xfe\x00\x01")

    assert response.status_code == 400
    assert "UTF-8" in response.json()["detail"]


# ---------------------------------------------------------------------------
# 8. Real cycle counts (needs M5)
# ---------------------------------------------------------------------------
@requires_runner
def test_basic_program_takes_seven_cycles(client, example_code):
    body = _simulate(client, example_code("basic.asm"))

    assert body["success"] is True
    assert body["total_cycles"] == 7
    assert body["stall_count"] == 0
    assert body["final_state"]["registers"]["R3"] == 30


@requires_runner
def test_load_use_program_takes_nine_cycles(client, example_code):
    body = _simulate(client, example_code("load_use.asm"))

    assert body["success"] is True
    assert body["total_cycles"] == 9
    assert body["stall_count"] == 1
    assert body["final_state"]["registers"]["R3"] == 40


@requires_runner
def test_independent_program_takes_nine_cycles(client, example_code):
    body = _simulate(client, example_code("independent.asm"))

    assert body["total_cycles"] == 9
    assert body["stall_count"] == 0


@requires_runner
def test_basic_program_forwards_in_cycle_five(client, example_code):
    body = _simulate(client, example_code("basic.asm"))
    cycle_five = body["history"][4]

    forwarded = {
        (item["register"], item["from_stage"]) for item in cycle_five["forwards"]
    }
    assert forwarded == {("R1", "WB"), ("R2", "MEM")}


@requires_runner
def test_load_use_program_stalls_in_cycle_five(client, example_code):
    body = _simulate(client, example_code("load_use.asm"))
    cycle_five = body["history"][4]

    assert cycle_five["stall"] is not None
    assert cycle_five["stall"]["register"] == "R2"
    assert "Load-use hazard" in cycle_five["stall"]["reason"]
    assert cycle_five["stages"]["ID"]["stalled"] is True


# ---------------------------------------------------------------------------
# 9. Every cycle carries forwards[] (even when empty)
# ---------------------------------------------------------------------------
def test_every_cycle_has_a_forwards_list(client):
    body = _simulate(client, SIMPLE_PROGRAM)

    assert body["history"]
    for cycle in body["history"]:
        assert isinstance(cycle["forwards"], list)
        assert "stall" in cycle
        assert set(cycle["stages"]) == {"IF", "ID", "EX", "MEM", "WB"}


# ---------------------------------------------------------------------------
# Placeholder mode (until M4/M5 are merged)
# ---------------------------------------------------------------------------
@requires_mock
def test_placeholder_timeline_is_flagged(client):
    body = _simulate(client, SIMPLE_PROGRAM)

    assert body["engine"] == "mock"
    assert body["warnings"], "placeholder responses must warn the caller"
    assert body["total_cycles"] == len(SIMPLE_PROGRAM.strip().splitlines()) + 4


# ---------------------------------------------------------------------------
# Contract shape
# ---------------------------------------------------------------------------
def test_success_and_failure_share_the_same_keys(client):
    ok = _simulate(client, SIMPLE_PROGRAM)
    bad = _simulate(client, "MULT R1, R2, R3")

    expected = {
        "success",
        "total_cycles",
        "stall_count",
        "forward_count",
        "instructions",
        "history",
        "final_state",
        "errors",
        "warnings",
        "engine",
    }
    assert expected <= set(ok)
    assert expected <= set(bad)
    assert bad["instructions"] == []
    assert bad["final_state"] == {"registers": {}, "memory": {}}


def test_cors_allows_the_vite_dev_server(client):
    response = client.options(
        "/api/simulate",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_service_upload_validation_is_reusable():
    from app.core.errors import UnsupportedFileTypeError

    with pytest.raises(UnsupportedFileTypeError):
        service.simulate_upload("notes.md", b"hello")


# ---------------------------------------------------------------------------
# The fixtures M6 and M7 develop against must match this contract
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", MOCK_FILES)
def test_frontend_mocks_match_the_contract(name):
    payload = json.loads((MOCKS_DIR / name).read_text(encoding="utf-8"))
    model = SimulationResponse.model_validate(payload)

    if name == "simulate-error.json":
        assert model.success is False
        assert model.errors[0].line == 2
    else:
        assert model.success is True
        assert len(model.history) == model.total_cycles


def test_mock_fixtures_cover_stalls_and_forwarding():
    success = json.loads((MOCKS_DIR / "simulate-success.json").read_text(encoding="utf-8"))
    load_use = json.loads((MOCKS_DIR / "simulate-load-use.json").read_text(encoding="utf-8"))

    # basic.asm: forwarding in C5, no stall
    assert success["total_cycles"] == 7
    assert success["stall_count"] == 0
    assert {
        (item["register"], item["from_stage"])
        for item in success["history"][4]["forwards"]
    } == {("R1", "WB"), ("R2", "MEM")}

    # load_use.asm: one stall in C5
    assert load_use["total_cycles"] == 9
    assert load_use["stall_count"] == 1
    assert load_use["history"][4]["stall"]["register"] == "R2"
    assert load_use["history"][4]["stages"]["ID"]["stalled"] is True

    for payload in (success, load_use):
        for cycle in payload["history"]:
            assert len(cycle["registers"]) == 32


# ---------------------------------------------------------------------------
# The service adapter: what happens once M5's runner is merged
# ---------------------------------------------------------------------------
def test_service_normalizes_a_runner_result(monkeypatch):
    from dataclasses import dataclass, field

    @dataclass
    class Cycle:
        cycle: int
        stages: dict
        forwards: list = field(default_factory=list)
        registers: dict = field(default_factory=dict)
        memory: dict = field(default_factory=dict)
        completed: int = 0
        stall: dict = None

    @dataclass
    class Result:
        total_cycles: int
        history: list
        final_state: dict

    history = [
        Cycle(
            cycle=1,
            stages={"IF": {"instruction_id": 0, "text": "LW R1, 0(R0)"}},
            registers={"R1": 0},
        ),
        Cycle(
            cycle=2,
            stages={
                "ID": {
                    "instruction": type(
                        "I", (), {"instruction_id": 1, "text": "ADD R2, R1, R0"}
                    )()
                }
            },
            forwards=[
                {
                    "register": "r1",
                    "from_stage": "wb",
                    "from_instruction": 0,
                    "to_instruction": 1,
                }
            ],
            registers={"R1": 7},
            memory={4: 7},
            completed=1,
            stall={"instruction_id": 1, "register": "r1", "reason": "Load-use hazard on R1"},
        ),
    ]

    monkeypatch.setattr(
        service,
        "_run_simulation",
        lambda instructions: Result(
            2, history, {"registers": {"R1": 7}, "memory": {4: 7}}
        ),
    )

    body = service.simulate_code("LW R1, 0(R0)\nADD R2, R1, R0")

    assert body.success is True
    assert body.engine == "real"
    assert body.total_cycles == 2
    assert body.stall_count == 1
    assert body.forward_count == 1
    assert len(body.history[0].registers) == 32
    assert body.history[1].stages.ID.instruction_id == 1
    assert body.history[1].memory == {"4": 7}
    assert body.history[1].stall.reason.startswith("Load-use hazard")
    assert body.final_state.memory == {"4": 7}

    dumped = body.model_dump(by_alias=True)
    forwarded = dumped["history"][1]["forwards"][0]
    assert forwarded["register"] == "R1"
    assert forwarded["from_stage"] == "WB"
    assert dumped["history"][1]["stall"]["register"] == "R1"


def test_service_reports_runner_errors_with_the_source_line(monkeypatch):
    from app.core.errors import SimulationError

    def boom(instructions):
        raise SimulationError(
            "Unaligned memory address: 2 (must be a multiple of 4)",
            instruction=instructions[1],
        )

    monkeypatch.setattr(service, "_run_simulation", boom)
    body = service.simulate_code("ADDI R1, R0, 2\nLW R2, 0(R1)\n")

    assert body.success is False
    assert body.history == []
    assert body.errors[0].line == 2
    assert body.errors[0].type == "simulation"


def test_service_turns_unexpected_crashes_into_internal_errors(monkeypatch):
    def boom(instructions):
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "_run_simulation", boom)
    body = service.simulate_code("ADDI R1, R0, 1")

    assert body.success is False
    assert body.errors[0].type == "internal"
    assert "boom" in body.errors[0].message


def test_service_enforces_the_cycle_limit(monkeypatch):
    class Result:
        total_cycles = 1001
        history = []
        final_state = {}

    monkeypatch.setattr(service, "_run_simulation", lambda instructions: Result())
    body = service.simulate_code("ADDI R1, R0, 1")

    assert body.success is False
    assert "1000 cycles" in body.errors[0].message
