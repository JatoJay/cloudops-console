import { insforge } from "@/lib/insforge/client";
import type {
  InvestigationResponse,
  InvestigationRun,
  InvestigationStep,
  ProgressEvent,
  ClusterListResponse,
} from "@/types/investigation";

export class InvestigationApiError extends Error {
  constructor(message: string, public guidance: string[] = []) {
    super(message);
  }
}

export async function getClusterContexts(): Promise<ClusterListResponse> {
  const response = await fetch("/api/clusters", { cache: "no-store" });
  const payload = await response.json();
  if (!response.ok) throw apiError(payload, "Could not load Kubernetes clusters");
  return payload as ClusterListResponse;
}

export async function getRecentInvestigations(): Promise<InvestigationRun[]> {
  const { data, error } = await insforge.database
    .from("investigation_runs")
    .select("id, namespace, status, current_step, root_cause, confidence, created_at")
    .order("created_at", { ascending: false })
    .limit(50);

  if (error) throw error;
  return (data ?? []) as InvestigationRun[];
}

export async function runInvestigation({
  userId,
  onProgress,
  context,
}: {
  userId: string;
  onProgress: (step: InvestigationStep) => void;
  context: string;
}): Promise<InvestigationResponse> {
  const investigationId = crypto.randomUUID();
  const channel = `investigation:${investigationId}`;
  const { error: insertError } = await insforge.database.from("investigation_runs").insert([
    {
      id: investigationId,
      user_id: userId,
      namespace: "all",
      status: "queued",
      current_step: "queued",
    },
  ]);

  if (insertError) throw insertError;

  const handleProgress = (payload: ProgressEvent) => {
    if (payload.meta?.channel && payload.meta.channel !== channel) return;
    if (payload.investigation_id === investigationId) onProgress(payload.current_step);
  };

  insforge.realtime.on("investigation_progress", handleProgress);
  const subscription = await insforge.realtime.subscribe(channel);
  if (!subscription.ok) {
    insforge.realtime.off("investigation_progress", handleProgress);
    await markInvestigationFailed(investigationId);
    throw new Error(subscription.error?.message ?? "Could not subscribe to investigation progress");
  }

  try {
    const response = await fetch("/api/investigate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ investigation_id: investigationId, namespace: "all", context }),
    });
    const payload = await response.json();
    if (!response.ok) throw apiError(payload, "Investigation failed");
    return payload as InvestigationResponse;
  } catch (error) {
    await markInvestigationFailed(investigationId);
    throw error;
  } finally {
    insforge.realtime.off("investigation_progress", handleProgress);
    insforge.realtime.unsubscribe(channel);
  }
}

function apiError(payload: Record<string, unknown>, fallback: string) {
  const detail = payload.detail;
  if (detail && typeof detail === "object") {
    const value = detail as { message?: string; guidance?: string[] };
    return new InvestigationApiError(value.message ?? fallback, value.guidance ?? []);
  }
  return new InvestigationApiError(
    typeof detail === "string"
      ? detail
      : typeof payload.message === "string"
        ? payload.message
        : fallback,
  );
}

async function markInvestigationFailed(investigationId: string) {
  await insforge.database
    .from("investigation_runs")
    .update({ status: "failed", current_step: "failed", updated_at: new Date().toISOString() })
    .eq("id", investigationId);
}
