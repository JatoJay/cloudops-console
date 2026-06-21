CREATE TABLE public.investigation_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  namespace TEXT NOT NULL DEFAULT 'all',
  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'running', 'completed', 'partial', 'failed')),
  current_step TEXT NOT NULL DEFAULT 'queued'
    CHECK (
      current_step IN (
        'queued',
        'checking_pods',
        'reading_logs',
        'analyzing_events',
        'inspecting_deployments',
        'checking_networking',
        'ai_reasoning',
        'root_cause_found',
        'failed'
      )
    ),
  root_cause TEXT,
  confidence INTEGER CHECK (confidence BETWEEN 0 AND 100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX investigation_runs_user_created_idx
  ON public.investigation_runs (user_id, created_at DESC);

ALTER TABLE public.investigation_runs ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.investigation_runs FROM anon, authenticated;
GRANT SELECT ON public.investigation_runs TO authenticated;
GRANT INSERT (id, user_id, namespace, status, current_step)
  ON public.investigation_runs TO authenticated;
GRANT UPDATE (status, current_step, root_cause, confidence, updated_at)
  ON public.investigation_runs TO authenticated;

CREATE POLICY investigation_runs_select_own
ON public.investigation_runs
FOR SELECT TO authenticated
USING (user_id = (SELECT auth.uid()));

CREATE POLICY investigation_runs_insert_own_queued
ON public.investigation_runs
FOR INSERT TO authenticated
WITH CHECK (
  user_id = (SELECT auth.uid())
  AND status = 'queued'
  AND current_step = 'queued'
  AND root_cause IS NULL
  AND confidence IS NULL
);

CREATE POLICY investigation_runs_update_own
ON public.investigation_runs
FOR UPDATE TO authenticated
USING (user_id = (SELECT auth.uid()))
WITH CHECK (user_id = (SELECT auth.uid()));

CREATE TRIGGER investigation_runs_updated_at
BEFORE UPDATE ON public.investigation_runs
FOR EACH ROW
EXECUTE FUNCTION system.update_updated_at();

INSERT INTO realtime.channels (pattern, description, enabled)
VALUES (
  'investigation:%',
  'Authenticated per-investigation progress updates',
  true
)
ON CONFLICT (pattern) DO UPDATE
SET description = EXCLUDED.description,
    enabled = EXCLUDED.enabled;

CREATE OR REPLACE FUNCTION public.can_access_investigation_channel(requested_channel TEXT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.investigation_runs
    WHERE id::text = split_part(requested_channel, ':', 2)
      AND user_id = (SELECT auth.uid())
  );
$$;

REVOKE ALL ON FUNCTION public.can_access_investigation_channel(TEXT) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.can_access_investigation_channel(TEXT) TO authenticated;

ALTER TABLE realtime.channels ENABLE ROW LEVEL SECURITY;

CREATE POLICY investigation_owner_subscribe
ON realtime.channels
FOR SELECT TO authenticated
USING (
  pattern = 'investigation:%'
  AND public.can_access_investigation_channel(realtime.channel_name())
);

CREATE OR REPLACE FUNCTION public.publish_investigation_progress()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, pg_temp
AS $$
BEGIN
  PERFORM realtime.publish(
    'investigation:' || NEW.id::text,
    'investigation_progress',
    jsonb_build_object(
      'investigation_id', NEW.id,
      'status', NEW.status,
      'current_step', NEW.current_step,
      'updated_at', NEW.updated_at
    )
  );

  RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.publish_investigation_progress() FROM PUBLIC, anon, authenticated;

CREATE TRIGGER publish_investigation_progress
AFTER UPDATE OF status, current_step ON public.investigation_runs
FOR EACH ROW
WHEN (
  OLD.status IS DISTINCT FROM NEW.status
  OR OLD.current_step IS DISTINCT FROM NEW.current_step
)
EXECUTE FUNCTION public.publish_investigation_progress();
