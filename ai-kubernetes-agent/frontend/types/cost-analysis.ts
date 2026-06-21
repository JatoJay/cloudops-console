export type Severity = "high" | "medium" | "low";

export type EstimatedSavings = {
  monthly: number;
  annual: number;
  currency: string;
};

export type CostIssue = {
  resource_id: string;
  resource_name: string;
  category: "over_provisioning" | "unused_or_idle" | "misconfiguration" | "wrong_pricing_tier" | "cost_optimization";
  severity: Severity;
  finding: string;
  rationale: string;
  estimated_savings: EstimatedSavings;
  fix_commands: string[];
};

export type CostAnalysis = {
  summary: string;
  issues: CostIssue[];
  estimated_savings: EstimatedSavings;
  assumptions: string[];
};

export type CostAnalysisResponse = CostAnalysis & { analysis_id: string };

export type AnalysisHistoryItem = {
  id: string;
  resource_group: string;
  resources_scanned: number;
  issues_found: number;
  estimated_savings: string;
  analysis_result: CostAnalysis;
  status: string;
  created_at: string;
};

export type ResourceGroupsResponse = { resource_groups: string[] };

export const analysisProgressSteps = [
  "Fetching resource groups...",
  "Scanning resources",
  "Analyzing costs with AI...",
  "Storing results...",
  "Analysis complete",
] as const;
