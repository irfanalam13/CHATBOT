# Enterprise AI Chatbot Platform — Frontend

A world-class, **white-label, multi-tenant** chatbot UI that drops onto any
ERP/CRM/HRM product. Built with **Next.js 15 (App Router) · TypeScript ·
Tailwind CSS v4 · TanStack Query · Zustand · React Hook Form · Zod**, talking to
the FastAPI backend in `../backend`.

> **One deliberate deviation from the spec:** the spec lists Socket.IO, but the
> backend streams over **SSE** (`POST /chat/completions`) and exposes a **native
> WebSocket** (`/chat/ws`). Socket.IO needs a Socket.IO server, which the backend
> is not — so streaming is implemented over SSE (`lib/chat-stream.ts`) with a
> native-WebSocket fallback. This is functionally equivalent and actually works
> against the backend as built.

---

## 1. Folder structure (feature-based)

```
frontend/
├── next.config.mjs            # proxies /api + /metrics → backend, package optimization
├── postcss.config.mjs         # Tailwind v4 via @tailwindcss/postcss
├── public/                    # manifest.webmanifest, sw.js (PWA/offline shell)
└── src/
    ├── app/                   # App Router
    │   ├── layout.tsx         # root: Providers, skip-link, metadata, PWA
    │   ├── globals.css        # Tailwind v4 + CSS-variable theme tokens (white-label)
    │   ├── login/page.tsx     # auth (RHF + Zod)
    │   └── (app)/             # authenticated shell (AuthGuard + AppShell)
    │       ├── chat/          # chat + sidebar
    │       ├── knowledge/     # KB management + upload
    │       ├── search/        # enterprise search
    │       ├── dashboard/     # analytics / cost / feedback
    │       └── settings/      # profile, appearance, AI/RAG, branding
    ├── components/            # ui/ primitives (shadcn-style), app-shell, guards, markdown
    ├── features/              # chat, sidebar, knowledge, branding (feature modules)
    ├── stores/                # Zustand: auth, chat, preferences
    └── lib/                   # api client, chat-stream (SSE/WS), types, rbac, utils, storage
```

## 2. Component tree (chat)

```
(app)/layout  → AuthGuard → ThemeInjector + AppShell(nav rail, topbar)
  chat/page
    ├─ ChatSidebar     (history · pinned · search · filters · rename/pin/archive/delete)
    └─ ChatWindow
        ├─ header       (KB selector · Sources toggle)
        ├─ MessageList → MessageBubble (Markdown · code · tables · Mermaid · Citations
        │                               · copy/regenerate/react/share/bookmark)
        ├─ live draft   (TypingIndicator → streamed tokens · tool chips · citations)
        ├─ Composer     (autosize · suggested questions · AI commands · stop)
        └─ RagPanel     (retrieved chunks · ranking bars · confidence)
```

## 3. State management

| Concern | Tool | Where |
|---|---|---|
| Server cache (sessions, messages, docs, analytics) | **TanStack Query** | `features/*/use-*.ts` |
| Auth/session + RBAC | **Zustand** | `stores/auth-store.ts` |
| Live streaming buffer (tokens, citations, tools) | **Zustand** | `stores/chat-store.ts` |
| Theme / a11y / preferences (persisted) | **Zustand** + persist | `stores/preferences-store.ts` |
| Forms + validation | **RHF + Zod** | `app/login`, settings |

## 4. API layer (`lib/api.ts`)

Typed client with **automatic refresh-token rotation** on 401 (single-flight),
typed `ApiError`, and `XMLHttpRequest` upload with progress. All calls go to
`/api/v1/*` and are proxied to the backend by `next.config.mjs` (same-origin →
no CORS in dev).

## 5. WebSocket / streaming layer (`lib/chat-stream.ts`)

`streamChat()` POSTs to `/chat/completions` and parses the SSE frame stream
incrementally into typed `ChatStreamEvent`s (`session → citations → token* →
tool_call/tool_result → done`). `openChatSocket()` provides the native-WS
alternative against `/chat/ws`.

## 6. Authentication flow

`login` → store tokens (`lib/storage.ts`) → `AuthGuard` bootstraps `me()`+`tenant()`
→ protected `(app)` routes render. Access token auto-refreshes via the rotation
endpoint; 401 after a failed refresh clears tokens and redirects to `/login`.
`PermissionGate` + `auth-store.can()` mirror the backend RBAC matrix for UI gating.

## 7. Chat flow

Composer → `useSendMessage` → `chat-store.send()` → `streamChat()` SSE loop →
tokens append to the live draft, citations + tool activity render in real time →
on `done`, TanStack Query invalidates `messages`/`sessions` to persist the turn.

## 8. RAG flow

The `citations` event drives both inline **Citations** (with confidence %, page,
source link, snippet preview) and the **RagPanel** (retrieved chunks, ranking
bars, document origin) — full RAG visualization per the spec.

## 9. Dashboard flow

`/dashboard` reads `analytics/dashboard`, `analytics/cost-by-model` and
`feedback/review-queue`; renders stat cards, a Recharts cost-by-model bar chart,
and the human-review queue.

## 10. Feature coverage map

| Spec area | Where |
|---|---|
| Chat window, bubbles, markdown, code, tables, mermaid, citations, streaming, typing | `features/chat/*`, `components/markdown/*` |
| Regenerate / copy / share / export / bookmark / reactions | `features/chat/message-bubble.tsx` |
| Sidebar: history, pinned, search, filters, archived | `features/sidebar/chat-sidebar.tsx` |
| Knowledge: drag&drop, bulk upload, progress, status, chunk viewer, versions, reprocess | `features/knowledge/*` |
| Search: global/semantic/hybrid/keyword, filters, source explorer | `app/(app)/search` |
| Dashboards: analytics, usage, cost, feedback | `app/(app)/dashboard` |
| User mgmt / roles / permissions | `auth-store`, `PermissionGate`, settings |
| Multi-tenant branding / custom theme / colors (white-label) | `globals.css` tokens, `features/branding`, settings → Branding |
| AI features: citations, confidence, memory, suggested questions, quick actions, AI commands, model selection | `features/chat/*`, settings → AI |
| RAG visualization | `features/chat/rag-panel.tsx` |
| Real-time: streaming, WebSockets, typing | `lib/chat-stream.ts` |
| Security: JWT, refresh, session mgmt, protected routes, permission guards | `lib/api.ts`, `auth-guard`, `permission-gate` |
| Accessibility: WCAG, keyboard nav, screen reader, high-contrast, reduced-motion | `globals.css`, skip-link, ARIA labels, preferences |
| Responsive + PWA + offline | responsive layouts, `manifest.webmanifest`, `sw.js` |
| Performance: code splitting, lazy mermaid import, caching, image opt, bundle opt | dynamic `import("mermaid")`, Query cache, `optimizePackageImports` |

## Quick start

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev          # http://localhost:3000  (proxies /api → http://localhost:8000)
```

Make sure the backend is running (`cd ../backend && docker compose up`) and
seeded (`demo` / `admin@demo.test` / `demo12345`).

```bash
npm run typecheck    # tsc --noEmit
npm run build        # production build
```

## Troubleshooting

**`Error: Missing field 'negated' on ScannerOptions.sources`** (CSS fails to
compile, `GET / 500`)
A Tailwind v4 version mismatch: `tailwindcss` / `@tailwindcss/postcss` are pinned
older than the transitively-resolved native scanner `@tailwindcss/oxide`, which
now requires a `negated` field the older PostCSS plugin doesn't send. Keep all
three on the **same** version, then reinstall:

```bash
# package.json — match these to the installed oxide (check: npm ls @tailwindcss/oxide)
#   "tailwindcss": "4.3.1",
#   "@tailwindcss/postcss": "4.3.1",
rm -rf node_modules package-lock.json   # PowerShell: Remove-Item -Recurse -Force node_modules, package-lock.json
npm install
npm ls tailwindcss @tailwindcss/postcss @tailwindcss/oxide   # all should report the same version
```

## Notes / next steps
- **Storybook & component tests** are scaffolding the spec calls for but aren't
  included here; the UI primitives in `components/ui` are deliberately isolated
  and prop-driven to make adding stories straightforward.
- App icons referenced by the manifest (`/icon-192.png`, `/icon-512.png`) should
  be added to `public/` for full PWA install.
- Custom-domain white-labeling is a deployment concern (map the domain to this
  app and pin `NEXT_PUBLIC_DEFAULT_TENANT`); per-tenant colors/logo are runtime
  via `features/branding`.
