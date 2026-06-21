"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { getAnalysisHistory, getResourceGroups, runCostAnalysis } from "@/services/cost-analysis";

export function useCostAnalysis(userId: string) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState<string[]>([]);

  const resourceGroups = useQuery({
    queryKey: ["cloud-resource-groups", userId],
    queryFn: getResourceGroups,
    refetchOnWindowFocus: false,
  });
  const history = useQuery({
    queryKey: ["cost-analysis-history", userId],
    queryFn: getAnalysisHistory,
  });
  const analysis = useMutation({
    mutationFn: (resourceGroup: string) => {
      if (!resourceGroup) throw new Error("Select a cloud resource group before running analysis");
      return runCostAnalysis({
        resourceGroup,
        onProgress: (message) => setProgress((current) => [...current, message]),
      });
    },
    onMutate: () => setProgress([]),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: ["cost-analysis-history", userId] });
      router.push(`/analysis/${result.analysis_id}`);
    },
  });

  return { resourceGroups, history, analysis, progress };
}

export function useAnalysisHistory(userId: string) {
  return useQuery({
    queryKey: ["cost-analysis-history", userId],
    queryFn: getAnalysisHistory,
  });
}
