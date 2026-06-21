export type InvestigationStep =
  | "queued"
  | "checking_pods"
  | "reading_logs"
  | "analyzing_events"
  | "inspecting_deployments"
  | "checking_networking"
  | "ai_reasoning"
  | "root_cause_found"
  | "failed";

export type Diagnosis = {
  root_cause: string;
  explanation: string;
  fix: string;
  kubectl_commands: string[];
  prevention_recommendation: string;
  confidence: number;
  confidence_reasoning: string[];
};

export type InvestigationResponse = {
  investigation_id: string;
  status: "success" | "partial";
  diagnosis: Diagnosis | null;
  errors: string[];
  investigation: Record<string, unknown>;
  message: string | null;
  guidance: string[];
  cluster_healthy: boolean;
};

export type ClusterListResponse = {
  status: "success" | "unavailable";
  contexts: string[];
  current_context: string | null;
  message: string | null;
  guidance: string[];
};

export type InvestigationRun = {
  id: string;
  namespace: string;
  status: "queued" | "running" | "completed" | "partial" | "failed";
  current_step: InvestigationStep;
  root_cause: string | null;
  confidence: number | null;
  created_at: string;
};

export type ProgressEvent = {
  investigation_id: string;
  status: InvestigationRun["status"];
  current_step: InvestigationStep;
  updated_at: string;
  meta?: { channel?: string };
};
