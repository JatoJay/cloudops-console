# Architecture

The project is an on-demand troubleshooting application:

1. Next.js restores the user's InsForge session and protects the dashboard.
2. The frontend creates an owner-scoped `investigation_runs` row and subscribes to its realtime channel.
3. The frontend sends the run ID to the authenticated FastAPI endpoint.
4. FastAPI orchestrates the investigation and updates the current step in InsForge.
5. The Kubernetes layer runs read-only `kubectl` commands and collects cluster evidence.
6. The AI layer sends a deterministic evidence prompt to OpenRouter and validates the structured diagnosis.
7. FastAPI stores the final root cause, confidence, and status; the frontend displays the diagnosis and recent history.

This application is not a Kubernetes controller or operator. Investigations and AI reasoning run only when requested through the API. Suggested kubectl commands are returned for human review and are never executed automatically.

InsForge is limited to identity, owner-scoped history, and realtime progress delivery. Row-level security restricts investigation rows and channels to their authenticated owner. OpenRouter credentials and Kubernetes access remain server-side.
