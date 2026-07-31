# Local development

This is the supported clean-clone path for the WeThePeople.place fork. It runs the API with a local SQLite database and disables startup network activity, so no API keys are required to boot the application.

## Prerequisites

- Git
- Python 3.11
- Node.js 20 and npm

## 1. Clone and configure

```bash
git clone https://github.com/wethepeople-place/WeThePeople.git
cd WeThePeople
cp .env.example .env
```

The checked-in example is safe for local development. Do not commit `.env`, database files, tokens, or production credentials. See [`ENVIRONMENT.md`](ENVIRONMENT.md) before enabling integrations.

## 2. Start the backend

macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn main:app --port 8006 --reload
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn main:app --port 8006 --reload
```

Verify `http://127.0.0.1:8006/health` and `http://127.0.0.1:8006/docs`.

## 3. Start the web frontend

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite reads `WTP_API_URL` from the repository-root `.env` and proxies `/api` to the backend.

## 4. Start the mobile app (optional)

Use a LAN-reachable backend URL for a physical phone; `127.0.0.1` refers to the phone itself.

```bash
cd mobile
npm ci
WTP_API_URL=http://192.168.1.10:8006 npm run start
```

In PowerShell, set `$env:WTP_API_URL` before `npm run start`. Expo web can be started with `npm run web`.

## Verification gate

Run these commands before opening a pull request:

```bash
python -m pytest -q tests/test_civic_slice_contract.py tests/test_committee_initialization.py tests/test_congress_legislators_import.py tests/test_vote_bill_backfill.py

cd frontend
npm ci
npm run build
npm test -- --run

cd ../mobile
npm ci
npx tsc --noEmit
```

The full inherited test suite contains known upstream failures and is not yet a merge gate. CI enforces the focused adoption tests, frontend build, and mobile type-check. It also runs frontend tests visibly as a non-blocking step; five stale tests (four API mocks and one timezone-sensitive date assertion) remain a separate repair.

## Common issues

- If backend startup contacts the Federal Register, confirm `.env` contains `DISABLE_STARTUP_FETCH=1`.
- If API requests return 401 locally, set both `WTP_ENV=development` and `WTP_REQUIRE_AUTH=0`; the application deliberately requires both.
- If the frontend reaches production, confirm `WTP_API_URL` is set in the root `.env` and restart Vite.
- A new SQLite database is expected to be mostly empty. Data ingestion is a separate, credentialed operation.
