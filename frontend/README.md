# OnlyNerds frontend

Vite + React + TypeScript. Talks to the existing backend (see `docs/`).

```bash
npm install
npm run dev     # http://localhost:3000
```

- The dev server is pinned to `localhost:3000` because the backend's CORS allows only that origin.
- Backend URL: `VITE_API_BASE_URL` (see `.env.example`), default `http://127.0.0.1:8000`.
- The master password is sent as `X-Master-Password` and kept in `localStorage`.
- `src/api/types.ts` is a copy of `docs/types.ts` (generated from the backend's OpenAPI schema).
- `src/api/client.ts` wraps only the routes verified in `docs/API_REFERENCE_CHECK.md`.
