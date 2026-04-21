-- ============================================================================
-- ecomtorials Research Hub — Migration 002
-- Adds fine-grained activity events so the frontend can animate the pipeline
-- live (agent spawn/finish + MCP tool calls).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- ENUMS
-- ----------------------------------------------------------------------------
CREATE TYPE research.agent_role AS ENUM (
  'step0',
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

CREATE TYPE research.activity_kind AS ENUM (
  'agent_spawn',
  'tool_call',
  'tool_result',
  'agent_finish',
  'note'
);

-- ----------------------------------------------------------------------------
-- TABLE
-- ----------------------------------------------------------------------------
CREATE TABLE research.job_activity (
  id          bigserial PRIMARY KEY,
  job_id      uuid NOT NULL REFERENCES research.jobs(id) ON DELETE CASCADE,
  agent       research.agent_role NOT NULL,
  kind        research.activity_kind NOT NULL,
  tool        text,
  detail      text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_job_activity_job ON research.job_activity (job_id, id);

-- ----------------------------------------------------------------------------
-- ROW LEVEL SECURITY — same pattern as job_steps (001 lines 170-180)
-- ----------------------------------------------------------------------------
ALTER TABLE research.job_activity ENABLE ROW LEVEL SECURITY;

CREATE POLICY job_activity_select_team
  ON research.job_activity
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM research.jobs j
      WHERE j.id = job_activity.job_id
        AND research.is_ecomtorials_user()
    )
  );

-- service_role bypasses RLS automatically.

-- ----------------------------------------------------------------------------
-- REALTIME
-- ----------------------------------------------------------------------------
ALTER PUBLICATION supabase_realtime ADD TABLE research.job_activity;

-- ----------------------------------------------------------------------------
-- GRANTS
-- ----------------------------------------------------------------------------
GRANT SELECT ON research.job_activity TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE research.job_activity_id_seq TO service_role;
