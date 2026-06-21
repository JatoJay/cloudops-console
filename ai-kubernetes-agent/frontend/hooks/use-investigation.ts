"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { getClusterContexts, runInvestigation } from "@/services/investigations";
import type { InvestigationStep } from "@/types/investigation";

export function useInvestigation(userId: string, context: string) {
  const queryClient = useQueryClient();
  const [currentStep, setCurrentStep] = useState<InvestigationStep>("queued");

  const clusters = useQuery({
    queryKey: ["kubernetes-contexts", userId],
    queryFn: getClusterContexts,
    refetchOnWindowFocus: false,
  });
  const activeContext = context
    || clusters.data?.current_context
    || clusters.data?.contexts[0]
    || "";
  const investigation = useMutation({
    mutationFn: () => {
      if (!activeContext) throw new Error("Select a Kubernetes cluster before investigating");
      return runInvestigation({ userId, context: activeContext, onProgress: setCurrentStep });
    },
    onMutate: () => setCurrentStep("queued"),
    onSuccess: (result) => {
      setCurrentStep(result.diagnosis || result.cluster_healthy ? "root_cause_found" : "failed");
      void queryClient.invalidateQueries({ queryKey: ["investigation-history", userId] });
    },
    onError: () => setCurrentStep("failed"),
  });

  return { currentStep, activeContext, clusters, investigation };
}
