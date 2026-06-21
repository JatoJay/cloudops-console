import type { VulnerabilityScanResponse } from "@/types/vulnerability";

export async function runVulnerabilityScan(context: string): Promise<VulnerabilityScanResponse> {
  const response = await fetch("/api/vulnerability-scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ context }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : typeof detail?.message === "string"
          ? detail.message
          : "Kubernetes vulnerability scan failed",
    );
  }
  return payload as VulnerabilityScanResponse;
}
