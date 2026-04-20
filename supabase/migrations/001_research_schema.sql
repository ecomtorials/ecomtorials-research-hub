-- ============================================================================
-- ecomtorials Research Hub — Initial Schema
-- Database: Knowledge Base (zxpweqryywixicirxkwu)
-- Schema: research (isoliert, berührt keine bestehenden Tables)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS research;

-- Allow authenticated users (via RLS below) and service_role to access the schema.
GRANT USAGE ON SCHEMA research TO authenticated, service_role;

-- ----------------------------------------------------------------------------
-- ENUM TYPES
-- ----------------------------------------------------------------------------
CREATE TYPE research.mode AS ENUM ('full', 'angle', 'ump_only', 'custom');

CREATE TYPE research.job_status AS ENUM (
  'queued',
  'running',
  'succeeded',
  'failed',
  'cancelled',
  'completed_with_warnings'
);

CREATE TYPE research.step_name AS ENUM (
  'step0_scrape',
  'r1a',
  'r1b',
  'r2_voc',
  'r3_prefetch',
  'r2_synth',
  'r3_scientist',
  'quality_review',
  'repair',
  'assembly_export'
);

CREATE TYPE research.step_status AS ENUM (
  'pending',
  'running',
  'succeeded',
  'failed',
  'skipped'
);

CREATE TYPE research.artifact_kind AS ENUM (
  'md',
  'docx',
  'briefing',
  'r1a',
  'r1b',
  'r2_raw',
  'r2_final',
  'r3_prefetch',
  'r3_final',
  'qr_scores',
  'cost_report'
);

-- ----------------------------------------------------------------------------
-- TABLES
-- ----------------------------------------------------------------------------

-- research.jobs — one row per research run
CREATE TABLE research.jobs (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id      uuid NOT NULL REFERENCES public.clients(id) ON DELETE RESTRICT,
  user_id        uuid NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
  mode           research.mode NOT NULL,
  custom_steps   research.step_name[],         -- only populated for mode='custom'
  source_job_id  uuid REFERENCES research.jobs(id) ON DELETE SET NULL,
                                               -- for mode='ump_only' when deriving from prior job
  url            text NOT NULL,
  brand          text NOT NULL,
  product_name   text,
  angle          text NOT NULL,
  status         research.job_status NOT NULL DEFAULT 'queued',
  cost_usd       numeric(10,4) NOT NULL DEFAULT 0,
  quality_score  numeric(4,2),
  error          text,
  drive_folder_url text,
  started_at     timestamptz,
  finished_at    timestamptz,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_jobs_user_created ON research.jobs (user_id, created_at DESC);
CREATE INDEX idx_jobs_client_created ON research.jobs (client_id, created_at DESC);
CREATE INDEX idx_jobs_status ON research.jobs (status) WHERE status IN ('queued','running');

-- research.job_steps — per-step telemetry, one row per step execution
CREATE TABLE research.job_steps (
  id             bigserial PRIMARY KEY,
  job_id         uuid NOT NULL REFERENCES research.jobs(id) ON DELETE CASCADE,
  step           research.step_name NOT NULL,
  status         research.step_status NOT NULL DEFAULT 'pending',
  started_at     timestamptz,
  finished_at    timestamptz,
  cost_usd       numeric(10,4) NOT NULL DEFAULT 0,
  chars_produced integer,
  turns          integer,
  log            text,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_job_steps_job ON research.job_steps (job_id, id);
CREATE UNIQUE INDEX idx_job_steps_job_step ON research.job_steps (job_id, step);

-- research.job_artifacts — metadata for each produced file (MD/DOCX/drafts/scores)
CREATE TABLE research.job_artifacts (
  id             bigserial PRIMARY KEY,
  job_id         uuid NOT NULL REFERENCES research.jobs(id) ON DELETE CASCADE,
  kind           research.artifact_kind NOT NULL,
  storage_path   text,         -- supabase storage object path (private bucket)
  drive_file_id  text,         -- google drive file id after upload
  drive_url      text,
  size_bytes     bigint NOT NULL DEFAULT 0,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_job_artifacts_job ON research.job_artifacts (job_id, kind);

-- ----------------------------------------------------------------------------
-- updated_at trigger for research.jobs
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION research.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_jobs_updated_at
BEFORE UPDATE ON research.jobs
FOR EACH ROW EXECUTE FUNCTION research.set_updated_at();

-- ----------------------------------------------------------------------------
-- ROW LEVEL SECURITY
-- Policy: only authenticated users with @ecomtorials.de email may read.
-- Writes are reserved for service_role (the worker + Next.js API routes).
-- ----------------------------------------------------------------------------
ALTER TABLE research.jobs           ENABLE ROW LEVEL SECURITY;
ALTER TABLE research.job_steps      ENABLE ROW LEVEL SECURITY;
ALTER TABLE research.job_artifacts  ENABLE ROW LEVEL SECURITY;

-- Helper: is the caller an ecomtorials employee?
CREATE OR REPLACE FUNCTION research.is_ecomtorials_user()
RETURNS boolean
LANGUAGE sql
STABLE
SET search_path = ''
AS $$
  SELECT coalesce(auth.jwt() ->> 'email', '') LIKE '%@ecomtorials.de';
$$;

-- jobs: ecomtorials users can read all team jobs; no direct writes.
CREATE POLICY jobs_select_team
  ON research.jobs
  FOR SELECT
  TO authenticated
  USING (research.is_ecomtorials_user());

-- job_steps: same read policy via parent job.
CREATE POLICY job_steps_select_team
  ON research.job_steps
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM research.jobs j
      WHERE j.id = job_steps.job_id
        AND research.is_ecomtorials_user()
    )
  );

-- job_artifacts: same read policy.
CREATE POLICY job_artifacts_select_team
  ON research.job_artifacts
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM research.jobs j
      WHERE j.id = job_artifacts.job_id
        AND research.is_ecomtorials_user()
    )
  );

-- service_role bypasses RLS automatically, so the worker and server routes
-- can INSERT/UPDATE without explicit policies.

-- ----------------------------------------------------------------------------
-- REALTIME
-- Enable replication on research.jobs and research.job_steps so the Next.js
-- browser client can subscribe to live updates for the current job.
-- ----------------------------------------------------------------------------
ALTER PUBLICATION supabase_realtime ADD TABLE research.jobs;
ALTER PUBLICATION supabase_realtime ADD TABLE research.job_steps;

-- ----------------------------------------------------------------------------
-- GRANTS
-- ----------------------------------------------------------------------------
GRANT SELECT ON ALL TABLES IN SCHEMA research TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA research TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA research TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA research TO service_role;

-- Default privileges for any future tables in this schema.
ALTER DEFAULT PRIVILEGES IN SCHEMA research
  GRANT SELECT ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA research
  GRANT ALL ON TABLES TO service_role;
