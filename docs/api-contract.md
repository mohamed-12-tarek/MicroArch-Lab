<!-- owner: M1 -->
# API Contract

The single source of truth for the JSON exchanged between the React app (M6/M7)
and the Python backend (M1/M2/M4/M5). **If you need a new field, change this
file first and tell the team.**

Base URL in development: `http://127.0.0.1:8000` · interactive docs: `/docs`

---

## 1. Endpoints

| Method | Path | Body | Success |
|---|---|---|---|
| `GET` | `/api/health` | – | `200` |
| `POST` | `/api/simulate` | `{"code": "..."}` | `200` |
| `POST` | `/api/simulate/upload` | `multipart/form-data`, field `file` | `200` |

### `GET /api/health`

```json
{
  "status": "ok",
  "version": "1.0.0",
  "engine": "real",
  "endpoints": ["/api/health", "/api/simulate", "/api/simulate/upload"]
}
```

`engine` is `"real"` once M5's `run_simulation` is merged, and `"mock"` while
the placeholder timeline is being served.

### `POST /api/simulate`

```json
{ "code": "ADDI R1, R0, 10\nADDI R2, R0, 20\nADD R3, R1, R2" }
```

* `code` is **required**. Missing or non-string → `422`.
* Maximum length: 100 000 characters → `422`.
* Empty code is **not** a `422`; it returns `success: false` with
  `"Program is empty"`.

### `POST /api/simulate/upload`

`multipart/form-data` with one field named `file`.

| Case | Status |
|---|---|
| `.asm` (case-insensitive) ≤ 100 KB, UTF-8 | `200` |
| any other extension | `400` |
| more than `102400` bytes | `413` |
| not valid UTF-8 | `400` |
| no `file` field | `422` |

A UTF-8 BOM is accepted. Comments (`#`, `;`) and blank lines are fine.

---

## 2. Response shape

`/api/simulate` and `/api/simulate/upload` return the **same object** for
success and failure, so the frontend never has to branch on which keys exist.

```json
{
  "success": true,
  "total_cycles": 7,
  "stall_count": 0,
  "forward_count": 2,
  "instructions": [],
  "history": [],
  "final_state": { "registers": {}, "memory": {} },
  "errors": [],
  "warnings": [],
  "engine": "real"
}
```

| Field | Type | Meaning |
|---|---|---|
| `success` | bool | `false` ⇒ `errors` is non-empty and `history` is empty |
| `total_cycles` | int | `N + 4 + number_of_stalls`; equals `len(history)` |
| `stall_count` | int | Load-Use stalls (the only kind) |
| `forward_count` | int | Sum of `len(cycle.forwards)` |
| `instructions` | array | The parsed program (see §3) |
| `history` | array | One entry per cycle, `cycle` is 1-based (see §4) |
| `final_state` | object | `registers` + `memory` after the last cycle |
| `errors` | array | See §5 |
| `warnings` | array of strings | Non-fatal notices (e.g. engine not connected) |
| `engine` | `"real"` \| `"mock"` | Which implementation answered |

### Important: invalid assembly is still HTTP 200

Parse and simulation errors are a **normal result**, not an HTTP failure:

```json
{
  "success": false,
  "total_cycles": 0,
  "stall_count": 0,
  "forward_count": 0,
  "instructions": [],
  "history": [],
  "final_state": { "registers": {}, "memory": {} },
  "errors": [
    { "line": 2, "message": "Unsupported instruction: MULT", "type": "parse" }
  ],
  "warnings": [],
  "engine": "real"
}
```

Only *transport* problems use a non-200 status: `400` (file type / encoding),
`413` (file size), `422` (bad request body).

---

## 3. `instructions[]`

```json
{
  "instruction_id": 2,
  "opcode": "ADD",
  "rd": "R3",
  "rs1": "R1",
  "rs2": "R2",
  "immediate": null,
  "line_number": 3,
  "raw": "ADD  R3, R1, R2",
  "text": "ADD R3, R1, R2"
}
```

* `instruction_id` starts at `0` and is the **row key** in the UI. Two identical
  instructions must stay two different rows.
* `line_number` is 1-based and counts blank/comment lines.
* `rd` is `null` for `SW` and `NOP`.

---

## 4. `history[]` — one entry per cycle

```json
{
  "cycle": 5,
  "stages": {
    "IF":  { "instruction_id": 3, "text": "ADD R3, R2, R0", "stalled": false },
    "ID":  null,
    "EX":  { "instruction_id": 2, "text": "LW R2, 0(R0)", "stalled": false },
    "MEM": { "instruction_id": 1, "text": "SW R1, 0(R0)", "stalled": false },
    "WB":  { "instruction_id": 0, "text": "ADDI R1, R0, 40", "stalled": false }
  },
  "forwards": [
    { "register": "R1", "from_stage": "MEM", "from_instruction": 0, "to_instruction": 1 }
  ],
  "registers": { "R0": 0, "R1": 40, "...": 0 },
  "memory": { "0": 40 },
  "completed": 1,
  "stall": null
}
```

* `stages` always has **all five keys**; `null` means the stage is empty
  (bubble) during that cycle.
* `registers` always contains **all 32 registers** `R0..R31` (a snapshot, not a
  reference). `R0` is always `0`.
* `memory` only contains addresses that were written; JSON keys are strings.
* `completed` = how many instructions have finished WB so far.
* `forwards` is **always present**, even when empty. Shape is fixed:

  ```json
  { "register": "R1", "from_stage": "MEM", "from_instruction": 0, "to_instruction": 2 }
  ```

  `from_stage` is `"MEM"` or `"WB"`. `from_instruction` / `to_instruction` are
  `instruction_id`s. `R0` is never forwarded.
* `stall` is `null` except on the cycle where the pipeline froze:

  ```json
  {
    "instruction_id": 3,
    "register": "R2",
    "reason": "Load-use hazard on R2: instruction 2 (LW R2, 0(R0)) is in EX"
  }
  ```

  On that cycle the instruction in `ID` has `"stalled": true`, `IF` is frozen
  and `EX` receives a bubble on the next cycle.

### Worked example — `basic.asm` (7 cycles)

```
cycle:   1    2    3    4    5    6    7
I0      IF   ID   EX   MEM  WB
I1           IF   ID   EX   MEM  WB
I2                IF   ID   EX   MEM  WB
                          ^ C5: forwards R1 (WB, I0) and R2 (MEM, I1) into I2
```

### Worked example — `load_use.asm` (9 cycles, 1 stall)

```
cycle:   1    2    3    4    5    6    7    8    9
I0      IF   ID   EX   MEM  WB
I1           IF   ID   EX   MEM  WB
I2                IF   ID   EX   MEM  WB
I3                     IF   ID*  ID   EX   MEM  WB
                             ^ C5: stall; C7: R2 forwarded from WB (I2)
```

---

## 5. `errors[]`

```json
{ "line": 2, "message": "Unsupported instruction: MULT", "type": "parse" }
```

| `type` | Who raises it | `line` |
|---|---|---|
| `parse` | M2 parser | the bad source line |
| `simulation` | M3 / M4 / M5 (`SimulationError`) | the instruction's line |
| `request` | M1 (bad upload) | `null` |
| `internal` | a bug in the simulator | `null` |

All parse errors are collected — three bad lines give three entries.

Message strings are fixed by `02_M2.md`, e.g.:

```text
Unsupported instruction: MULT
Invalid operand count for ADD: expected 3, got 2
Invalid register: R32
Invalid immediate: abc
Immediate out of range (-32768..32767): 40000
Program is empty
```

The frontend renders them as `Line 2: Unsupported instruction: MULT` and falls
back to the bare message when `line` is `null`.

---

## 6. Mock fixtures (`frontend/src/mocks/`)

M6/M7 develop against these until the backend is wired. They are validated
against the real Pydantic schema by `backend/tests/test_api.py`.

| File | Program | Cycles | Stalls | Forwards |
|---|---|---|---|---|
| `simulate-success.json` | `basic.asm` | 7 | 0 | 2 (C5: R1←WB, R2←MEM) |
| `simulate-load-use.json` | `load_use.asm` | 9 | 1 (C5, R2) | 2 |
| `simulate-memory.json` | `memory.asm` | 8 | 0 | 3, memory `{"8": 100}` |
| `simulate-error.json` | `MULT` on line 2 | 0 | 0 | 0 |

---

## 7. Internal contract for M4 / M5

`app/api/service.py` calls exactly one function:

```python
run_simulation(instructions: list[Instruction]) -> SimulationResult
```

`SimulationResult` may be a dataclass, a dict or a pydantic model. The service
accepts any of these fields:

| Field | Required | Notes |
|---|---|---|
| `history` | yes | list of cycle objects; each may be a dict, a dataclass or have `to_dict()` |
| `total_cycles` | no | defaults to `len(history)` |
| `stall_count` | no | defaults to cycles where `stall` is not `None` |
| `forward_count` | no | defaults to the sum of `len(cycle.forwards)` |
| `final_state` | no | `{"registers": {...}, "memory": {...}}`; defaults to the last cycle |

Each cycle object should provide `cycle`, `stages` (dict of `IF/ID/EX/MEM/WB`,
each `None` or a slot with `instruction_id` + `text` + `stalled`), `forwards`,
`registers`, `memory`, `completed` and `stall`.

**Errors:** raise `app.core.errors.SimulationError("message", instruction=instr)`
from the engine so the response carries the source line. Never let a raw
`ValueError` escape — the service will report it as `internal` without a line.

**Cycle limit:** stop after `MAX_CYCLES = 1000` and raise a `SimulationError`.

**Hazard unit:** `detect_hazard(id_instruction, ex_instruction)` currently
returns `(should_stall, message)` and `resolve_forwarding(ex, mem, wb)` returns
`{register: {"from_stage": ..., "from_instruction": ...}}`. M4 must consume that
shape (see `docs/architecture.md` §Known mismatches).
