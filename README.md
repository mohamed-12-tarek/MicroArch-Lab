<!-- owner: M1 -->
# MicroArch Lab

A cycle-accurate **5-stage pipeline simulator** for a small RISC ISA.
You write assembly (or upload a `.asm` file), the Python backend runs it on a
virtual processor **one clock cycle at a time**, and the React frontend draws a
table showing which instruction was in which stage during every cycle.

```
IF → ID → EX → MEM → WB
```

* **ISA:** `ADD SUB AND OR ADDI LW SW NOP`, registers `R0..R31` (`R0` is always 0)
* **Hazards:** full forwarding (MEM → EX, WB → EX); the only stall is **Load-Use**, and it costs exactly one cycle
* **Formula:** `total_cycles = N + 4 + number_of_stalls`
* **Errors:** every bad line is reported with its line number — the parser never stops at the first one

---

## Quick start

### Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

* API: <http://127.0.0.1:8000>
* Swagger UI: <http://127.0.0.1:8000/docs>
* Health check: <http://127.0.0.1:8000/api/health>

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

The dev server talks to `http://127.0.0.1:8000` and is allowed by CORS.
To run the UI without a backend, start it with the mock fixtures:

```bash
# .env.local
VITE_USE_MOCK=true
```

> The frontend lands with M6/M7; until `frontend/package.json` is merged the
> backend works on its own.

---

## Try it in 30 seconds

```bash
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H "Content-Type: application/json" \
  -d "{\"code\": \"ADDI R1, R0, 10\nADDI R2, R0, 20\nADD R3, R1, R2\"}"
```

The response contains `total_cycles: 7`, the 3 parsed instructions and 7 cycle
snapshots. Cycle 5 shows two forwarded values:

```json
"forwards": [
  { "register": "R1", "from_stage": "WB",  "from_instruction": 0, "to_instruction": 2 },
  { "register": "R2", "from_stage": "MEM", "from_instruction": 1, "to_instruction": 2 }
]
```

Upload a file instead:

```bash
curl -X POST http://127.0.0.1:8000/api/simulate/upload -F "file=@examples/load_use.asm"
```

Invalid code is **not** an HTTP error — it returns `200` with `success: false`
and the offending lines:

```json
{
  "success": false,
  "errors": [{ "line": 2, "message": "Unsupported instruction: MULT", "type": "parse" }]
}
```

---

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | liveness + which engine is wired in |
| `POST` | `/api/simulate` | `{"code": "..."}` → full timeline |
| `POST` | `/api/simulate/upload` | `multipart` `.asm` (≤ 100 KB) → full timeline |

Status codes: `200` result (even for invalid assembly) · `400` wrong file type
or encoding · `413` file too large · `422` malformed body.

The complete JSON contract — including `forwards`, `stall`, the 32 registers and
the mock fixtures — is in [`docs/api-contract.md`](docs/api-contract.md).

---

## Examples

| File | Cycles | Stalls | Result |
|---|---|---|---|
| `basic.asm` | 7 | 0 | `R1=10 R2=20 R3=30` |
| `independent.asm` | 9 | 0 | `R1..R5 = 1..5` |
| `arithmetic.asm` | 10 | 0 | `R3=22 R4=2 R5=8 R6=14` |
| `memory.asm` | 8 | 0 | `R3=100`, memory `{"8": 100}` |
| `load_use.asm` | 9 | 1 | `R3=40` |
| `forwarding.asm` | 8 | 0 | `R1=1 R2=2 R3=4 R4=8` |
| `nop_and_r0.asm` | 8 | 0 | `R2=7` |
| `error_unsupported_opcode.asm` | – | – | parse error, line 2 |
| `error_memory_alignment.asm` | – | – | simulation error, line 2 |

---

## Tests

```bash
# backend
cd backend
pytest -q                 # add -v for the list, --cov=app for coverage

# frontend
cd frontend
npm test -- --run
npm run build
```

The CI in `.github/workflows/ci.yml` runs the backend suite on every push and
pull request, and the frontend suite + build once `frontend/package-lock.json`
exists.

---

## Project structure

```text
backend/app/
  main.py                 FastAPI app, CORS, error handlers
  api/routes.py           the 3 endpoints
  api/service.py          parse → run → response (the integration point)
  schemas/                Pydantic request/response models
  core/                   instruction, parser, ALU, registers, memory,
                          control unit, processor, hazard unit, runner
  simulator/              pipeline state, cycle engine, history
backend/tests/            pytest suites + golden results
docs/                     isa-spec · api-contract · architecture · test-plan
examples/                 the nine reference programs
frontend/src/             React app (M6 rendering, M7 editor/API)
```

Architecture, layer rules and the request lifecycle are documented in
[`docs/architecture.md`](docs/architecture.md).

---

## Team & workflow

| Owner | Area | Branch |
|---|---|---|
| **M1** | repo, CI, API, integration | `feature/backend-api` |
| **M2** | `instruction.py`, `parser.py` | `feature/assembly-parser` |
| **M3** | ALU, registers, memory, control, processor | `feature/processor-core` |
| **M4** | pipeline state + cycle engine | `feature/pipeline-engine` |
| **M5** | hazard unit, history, runner, golden tests | `feature/pipeline-runner` |
| **M6** | timeline table + viewers | `feature/pipeline-visualization` |
| **M7** | editor, upload, API client, page | `feature/react-interface` |

Rules:

1. One owner per file — never edit someone else's file, ask them.
2. Nobody pushes to `main`: branch → PR → review by the next person in the chain.
3. Every PR must be rebased first: `git fetch origin && git rebase origin/main`, then run the tests.
4. Everyone writes the tests for their own part.

### Current status

| Part | State |
|---|---|
| M1 API, schemas, errors, CI, mocks, docs | ✅ done |
| M2 instruction + parser | ✅ merged |
| M3 ALU, registers, memory | ✅ merged · control unit + processor pending |
| M4 engine, M5 runner | ⏳ pending — the API serves a flagged placeholder until then |
| M6, M7 UI | ⏳ pending |

When M5 merges `run_simulation`, the API switches to the real engine
automatically (`engine: "real"`) — no change needed in `service.py`.

---

## Release

```bash
git tag -a v1.0.0 -m "MicroArch Lab v1.0.0"
git push origin v1.0.0
```
