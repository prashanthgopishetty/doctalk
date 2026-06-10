---
description: "Use when writing or modifying Next.js frontend components, API routes, CopilotKit integration, Tailwind styling, or TypeScript types for the DocTalk frontend. Covers App Router patterns, CopilotKit hooks, AG-UI bridge setup, and TypeScript strict mode."
applyTo: "frontend/**/*.{ts,tsx}"
---

# Frontend — Next.js + CopilotKit Conventions

## TypeScript Rules
- Strict mode ON — no `any`; use `unknown` for external/untyped data
- Explicit return types on all exported functions and components
- Prefer `type` over `interface` for object shapes; use `interface` for extension hierarchies
- Use `satisfies` operator for typed literals with inference

```typescript
// Good
const config = {
  agentUrl: process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000",
} satisfies AppConfig;
```

## Next.js App Router Rules
- All server components are `async` by default — add `"use client"` only when needed
- API routes live in `app/api/<route>/route.ts` — export named `GET`, `POST`, etc.
- Never use `pages/` directory — always `app/`
- Environment variables: prefix with `NEXT_PUBLIC_` for client-side access

## CopilotKit Integration

### Provider Setup (layout.tsx)
```tsx
import { CopilotKit } from "@copilotkit/react-core";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CopilotKit runtimeUrl="/api/copilotkit">
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
```

### AG-UI Bridge Route (app/api/copilotkit/route.ts)
```typescript
import { CopilotRuntime, copilotRuntimeNextJSAppRouterEndpoint } from "@copilotkit/runtime";
import { RemoteRuntime } from "@copilotkit/runtime";
import { NextRequest } from "next/server";

const runtime = new CopilotRuntime({
  remoteEndpoints: [
    new RemoteRuntime({ url: process.env.BACKEND_URL ?? "http://localhost:8000/agent" }),
  ],
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
```

### Reading Agent State
```typescript
import { useCoAgent } from "@copilotkit/react-core";

const { state, setState } = useCoAgent<DocTalkState>({
  name: "doctalk_agent",
  initialState: { codebaseId: null, agentHint: "auto" },
});
```

### Shared Readable Context
```typescript
import { useCopilotReadable } from "@copilotkit/react-core";

useCopilotReadable({
  description: "Currently ingested codebase",
  value: { id: codebaseId, source: codebaseSource },
});
```

## Component Patterns
- Functional components only — no class components
- Name components in PascalCase matching their filename
- Props types defined inline with the component unless shared:

```tsx
type ChatPanelProps = {
  codebaseId: string | null;
  agentHint: AgentType;
};

export function ChatPanel({ codebaseId, agentHint }: ChatPanelProps): React.ReactElement {
  ...
}
```

## Tailwind Rules
- Prefer utility classes — no custom CSS unless unavoidable
- Dark mode: use `dark:` prefix with `class` strategy
- Responsive: mobile-first (`sm:`, `md:`, `lg:` prefixes)
- Color palette: use `slate-` for neutrals, `violet-` for primary accents

## Fetch Patterns
```typescript
// Always use relative paths for same-origin calls
const res = await fetch("/api/copilotkit", { method: "POST", ... });
if (!res.ok) {
  const error: unknown = await res.json();
  throw new Error(`Request failed: ${res.status}`);
}
```

## File Structure Rules
- One component per file; export as named export
- Types shared between components go in `lib/types.ts`
- Server-only logic goes in `lib/server/` with `"server-only"` import
