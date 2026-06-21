import type {
  AnalysisHistoryItem,
  CostAnalysisResponse,
  ResourceGroupsResponse,
} from "@/types/cost-analysis";
import { insforge } from "@/lib/insforge/client";

export class CostAnalysisApiError extends Error {}

export async function getResourceGroups(): Promise<ResourceGroupsResponse> {
  return authenticatedRequest<ResourceGroupsResponse>("/api/resource-groups");
}

export async function getAnalysisHistory(): Promise<AnalysisHistoryItem[]> {
  return authenticatedRequest<AnalysisHistoryItem[]>("/api/history");
}

export async function runCostAnalysis({
  projectId,
  connectionId,
  onProgress,
}: {
  projectId: string;
  connectionId: string;
  onProgress: (message: string) => void;
}): Promise<CostAnalysisResponse> {
  const analysisId = crypto.randomUUID();
  const accessToken = await getAccessToken();
  const responsePromise = fetch(`${apiBaseUrl()}/api/analyze`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      analysis_id: analysisId,
      resource_group: projectId,
      project_id: projectId,
      connection_id: connectionId,
    }),
  });
  const socket = new WebSocket(progressSocketUrl(analysisId), ["bearer", accessToken]);
  socket.addEventListener("message", (event) => onProgress(String(event.data)));

  await new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => reject(new Error("Live progress connection timed out")), 8_000);
    socket.addEventListener("open", () => {
      window.clearTimeout(timeout);
      resolve();
    }, { once: true });
    socket.addEventListener("error", () => {
      window.clearTimeout(timeout);
      reject(new Error("Could not connect to live progress"));
    }, { once: true });
  });
  try {
    return await parseJsonResponse<CostAnalysisResponse>(await responsePromise);
  } finally {
    if (socket.readyState === WebSocket.OPEN) socket.close();
  }
}

function progressSocketUrl(analysisId: string): string {
  const configured = process.env.NEXT_PUBLIC_BACKEND_WS_URL?.replace(/\/$/, "");
  if (configured) return `${configured}/ws/progress/${analysisId}`;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.hostname}:8000/ws/progress/${analysisId}`;
}

async function authenticatedRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const accessToken = await getAccessToken();
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    cache: "no-store",
    ...init,
    headers: { ...init?.headers, Authorization: `Bearer ${accessToken}` },
  });
  return parseJsonResponse<T>(response);
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail;
    throw new CostAnalysisApiError(
      typeof detail === "string"
        ? detail
        : typeof detail?.message === "string"
          ? detail.message
          : typeof payload.message === "string"
            ? payload.message
            : "Cloud cost analysis failed",
    );
  }
  return payload as T;
}

async function getAccessToken(): Promise<string> {
  await insforge.auth.getCurrentUser();
  const token = document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith("insforge_access_token="))
    ?.split("=")
    .slice(1)
    .join("=");
  if (!token) throw new CostAnalysisApiError("Your session has expired. Sign in again.");
  return decodeURIComponent(token);
}

function apiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");
}
