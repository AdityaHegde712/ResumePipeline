# Resume Pipeline — Frontend

Slim dark-minimal UI for the Resume Pipeline backend. React 19 + Vite + TypeScript + Mantine v9.

## What it does

- Form: `job_position`, `company_name`, optional `company_description`, `job_description`.
- POSTs to `POST /api/applications`; shows per-phase status chips
  (`llm_generation`, `reconstruction`, `saved`, `pdf_error`) with green check / red x.
- Displays the raw `llm_response.md` in a read-only monospace textarea.
- Export dropdown: TeX or PDF, downloaded as attachments
  (`GET /api/applications/{id}/tex`, `/pdf`) — enabled after a successful run.

## Setup

```bash
npm install
```

## Dev

```bash
npm run dev        # http://localhost:5173
```

The Vite dev server proxies `/api` to `http://localhost:8000` (the FastAPI backend).

## Test & build

```bash
npm run test       # vitest — API client unit tests (mocked fetch, no browser)
npm run build      # tsc -b && vite build
```
