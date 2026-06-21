# CloudOps Console

A cloud operations workspace with a FastAPI backend and Next.js frontend. It combines
Kubernetes troubleshooting, cluster vulnerability scanning, and AI-powered multi-cloud
cost analysis in one authenticated application.

The backend collects Kubernetes evidence through read-only `kubectl` commands, then asks an OpenRouter model to produce a structured, evidence-grounded diagnosis.

## Run with Docker

```bash
docker compose up --build
```

Then open:

- Frontend: <http://localhost:3000>
- Backend health: <http://localhost:8000/health>

Sign in with an existing SantaProjects InsForge email/password account. The dashboard and investigation API are protected; unauthenticated investigation requests return `401`.

The dashboard lists every context visible in the backend's kubeconfig and marks the current context as the default selection. Investigations always pass the selected context explicitly to kubectl.

Without cluster credentials, `POST /investigate` still returns a structured `partial` response that explains which commands failed. When evidence is available, the response also includes root cause, explanation, suggested fix, reviewable kubectl commands, prevention guidance, and a calibrated confidence score.

## Configure AI reasoning

From the linked repository root, fetch the InsForge project's active OpenRouter key into the backend's ignored env file:

```bash
npx @insforge/cli ai setup --env-file ai-kubernetes-agent/backend/.env
```

Then set a structured-output-capable model in `backend/.env`:

```env
OPENROUTER_MODEL=openai/gpt-4.1-mini
```

The API key is server-only. Never move it into a frontend-prefixed environment variable or commit `backend/.env`.

## Investigate a Kubernetes cluster

For public deployments, use the outbound cluster agent instead of mounting a user's kubeconfig into the hosted backend. Open **Kubernetes → Connect**, generate a 15-minute pairing token, and run the displayed Helm command. The agent:

- opens outbound HTTPS/WebSocket connections only;
- uses a dedicated ServiceAccount with `get`, `list`, and `watch` access;
- cannot read Kubernetes Secrets and has no mutation verbs;
- stores jobs durably in InsForge so queued work survives reconnects;
- sends scan results to the owning user's account under RLS isolation.

The chart is in `helm/cloudops-agent`. Publish the backend container image and set its repository in `values.yaml`; that same image can run the control plane or `python -m app.cluster_agent`. The control plane requires server-only `INSFORGE_API_KEY` and `PUBLIC_API_URL` values. Treat pairing tokens as credentials and never place them in source control.

For local CLI use without Helm:

```bash
cd backend
python -m app.cluster_agent \
  --control-plane https://your-console.example.com \
  --token coa_REPLACE_ME \
  --cluster-name production \
  --kubeconfig "$HOME/.kube/config"
```

The older direct-kubeconfig mode below remains useful for local development.

The Docker image includes `kubectl`. Mount a kubeconfig explicitly when the backend should access a cluster:

```bash
HOST_KUBECONFIG_DIR="$HOME/.kube" \
  docker compose -f docker-compose.yml -f docker-compose.kubernetes.yml up --build
```

If the kubeconfig references external certificate files, first create a portable ignored copy with embedded credentials:

```bash
mkdir -p .kube-docker
kubectl config view --raw --flatten > .kube-docker/config
HOST_KUBECONFIG_DIR="$PWD/.kube-docker" \
  docker compose -f docker-compose.yml -f docker-compose.kubernetes.yml up --build
```

Then start an investigation from the authenticated dashboard. Direct API calls must include a current InsForge access token:

```bash
curl -X POST http://localhost:8000/investigate \
  -H "Authorization: Bearer $INSFORGE_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"namespace":"all"}'
```

The response contains the five evidence sections plus an AI diagnosis. The executor only permits read-only `kubectl` command families and never invokes a shell. AI-proposed commands are returned for human review and are never executed by the application.

The Kubernetes page also provides an authenticated vulnerability scan powered by Trivy.
It scans cluster components, workload images, Kubernetes configuration, and potential
secret exposure. The node collector is disabled so an on-demand scan does not create
privileged collector pods. Docker builds include Trivy; local development requires
`brew install trivy` on macOS or an equivalent official Trivy installation.

## Test intentional failures

Reproducible CrashLoopBackOff, ImagePullBackOff, OOMKilled, and service-selector mismatch fixtures live in `kubernetes/test-scenarios`. Apply them only to a disposable local cluster; the included guide also provides the one-command cleanup.

`KUBECTL_VERSION` can override the container's default kubectl version at build time. Choose a kubectl client within one minor version of the target cluster.

## Environment

Copy the example files when running outside Docker:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

The investigation layer uses `KUBECONFIG_PATH`, `KUBECTL_TIMEOUT_SECONDS`, `KUBECTL_LOG_TAIL_LINES`, `CONTAINER_CREATING_TIMEOUT_SECONDS`, and `VULNERABILITY_SCAN_TIMEOUT_SECONDS`. AI reasoning uses `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_TIMEOUT_SECONDS`, `OPENROUTER_MAX_RETRIES`, and `OPENROUTER_MAX_TOKENS`.

Cloud cost analysis uses the server's active Google Cloud CLI account and project. Run
`gcloud auth login` and `gcloud config set project PROJECT_ID`, then call
`POST /api/analyze`; the backend uses Cloud Asset Inventory to collect GCP resources before sending them to the
InsForge-configured OpenRouter gateway. `COST_ANALYSIS_MODEL` defaults to
`openai/gpt-4o`. `GCP_PROJECT_ID` can override the active project, and
`CLOUD_SCAN_TIMEOUT_SECONDS` controls the inventory timeout. The
returned commands are recommendations for human review and are never executed.

Authenticated cloud analysis clients may generate a UUID, connect to
`ws://localhost:8000/ws/progress/<analysis-id>`, and send that UUID as `analysis_id`
to `POST /api/analyze`. The socket receives stage messages through completion. Past
results are available from authenticated `GET /api/history` requests and are isolated
per user through InsForge row-level security.

Authentication, investigation history, and progress events use `INSFORGE_URL`, `NEXT_PUBLIC_INSFORGE_URL`, and `NEXT_PUBLIC_INSFORGE_ANON_KEY`. Cluster-agent pairing and job updates additionally use the server-only `INSFORGE_API_KEY`; generated install commands use `PUBLIC_API_URL`. Keep the anonymous key in ignored local environment files even though it is a public browser credential. Never expose the InsForge server key or OpenRouter key to the frontend.

## InsForge data model

The migration in the repository-level `migrations` directory creates `investigation_runs`, owner-only RLS policies, and an owner-authorized realtime channel pattern. Apply it through the linked InsForge CLI before running against a new project. The frontend creates a queued run, subscribes to `investigation:<run-id>`, and then asks FastAPI to perform the investigation. FastAPI remains the only investigation orchestrator and publishes progress by updating the run.

## Local development

Backend (Python 3.12+):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Frontend (Node.js 22+):

```bash
cd frontend
npm install
npm run dev
```

## Structure

- `backend/app/api`: HTTP routes
- `backend/app/core`: configuration and logging
- `backend/app/kubernetes`: kubectl executor and evidence collectors
- `backend/app/ai`: prompt building, OpenRouter client, diagnosis validation, fixes, and confidence calibration
- `backend/app/services`: investigation orchestration
- `backend/app/models`: Pydantic models
- `frontend/components`: reusable UI components
- `frontend/services`: API clients
- `frontend/hooks`: React Query hooks
- `frontend/types`: shared frontend types
- `docs`: architecture documentation
- `prompts`: future AI prompt templates
