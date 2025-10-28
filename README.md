# Learn Gen

Local, animation-first explainer generator.

## Frontend Quickstart

The Next.js interface lives at the repository root.

### Install dependencies

```bash
pnpm install
# or
npm install
```

### Environment variables

Create `.env.local` alongside `package.json`:

```bash
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

Swap the value when targeting a remote API.

### Run the development server

```bash
pnpm dev
# or
npm run dev
```

Navigate to http://localhost:3000 to launch the Learn Gen UI.

## Workflow Notes

- The Generate form validates with `react-hook-form` + `zod` and posts to `${NEXT_PUBLIC_API_BASE}/v1/generate` with the payload expected by the orchestration backend (length, aspect, visuals, voice, research toggles).
- Advanced options expose target height, voice model path, pace WPM, and web search flag; target height defaults swap automatically between portrait (1920) and other aspects (1080).
- The results panel auto-detects MP4 URLs for inline preview. Non-remote paths display a copy helper plus an SCP command (`scp -P <EXTERNAL_SSH_PORT> root@<EXTERNAL_IP>:<path> .`); use “Edit defaults” to persist the SSH host/port in `localStorage`.
- A collapsible log shows the raw JSON response for troubleshooting.

Run the existing FastAPI backend separately before submitting jobs through the frontend.
