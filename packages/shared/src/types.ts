export type ResearchMode = 'full' | 'angle' | 'ump_only' | 'custom';

export type PipelineStep =
  | 'step0_scrape'
  | 'r1a'
  | 'r1b'
  | 'r2_voc'
  | 'r3_prefetch'
  | 'r2_synth'
  | 'r3_scientist'
  | 'quality_review'
  | 'repair'
  | 'assembly_export';

export type JobStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled'
  | 'completed_with_warnings';

export interface JobPayload {
  jobId: string;
  clientId: string;
  mode: ResearchMode;
  customSteps?: PipelineStep[];
  url: string;
  brand: string;
  productName?: string;
  angle: string;
  sourceJobId?: string;
}

export interface JobStepRecord {
  step: PipelineStep;
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped';
  startedAt?: string;
  finishedAt?: string;
  costUsd?: number;
  charsProduced?: number;
  log?: string;
}

export type ArtifactKind =
  | 'md'
  | 'docx'
  | 'briefing'
  | 'r1a'
  | 'r1b'
  | 'r2_raw'
  | 'r2_final'
  | 'r3_prefetch'
  | 'r3_final'
  | 'qr_scores'
  | 'cost_report';

export interface JobArtifact {
  jobId: string;
  kind: ArtifactKind;
  storagePath?: string;
  driveFileId?: string;
  sizeBytes: number;
}
