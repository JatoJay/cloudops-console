CREATE TABLE public.analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  resource_group TEXT NOT NULL,
  resources_scanned INTEGER NOT NULL CHECK (resources_scanned >= 0),
  issues_found INTEGER NOT NULL CHECK (issues_found >= 0),
  estimated_savings TEXT NOT NULL,
  analysis_result JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'completed'
    CHECK (status IN ('queued', 'running', 'completed', 'failed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX analyses_user_created_idx
  ON public.analyses (user_id, created_at DESC);

ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.analyses FROM anon, authenticated;
GRANT SELECT ON public.analyses TO authenticated;
GRANT INSERT (
  id,
  user_id,
  resource_group,
  resources_scanned,
  issues_found,
  estimated_savings,
  analysis_result,
  status
) ON public.analyses TO authenticated;

CREATE POLICY analyses_select_own
ON public.analyses
FOR SELECT TO authenticated
USING (user_id = (SELECT auth.uid()));

CREATE POLICY analyses_insert_own_completed
ON public.analyses
FOR INSERT TO authenticated
WITH CHECK (
  user_id = (SELECT auth.uid())
  AND status = 'completed'
);
