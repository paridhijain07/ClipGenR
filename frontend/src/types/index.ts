export type JobStage =
  | "QUEUED"
  | "EXTRACTING_AUDIO"
  | "TRANSCRIBING"
  | "ANALYZING_SEMANTICS"
  | "RANKING_CLIPS"
  | "CROPPING_RENDERING"
  | "COMPLETED"
  | "FAILED";

export type VideoStatus = "PENDING" | "UPLOADING" | "PROCESSING" | "COMPLETED" | "FAILED";

export type ClipStatus = "PENDING" | "READY" | "RENDERING" | "FAILED";

export interface ScoreBreakdown {
  hook_strength: number;
  emotional_resonance: number;
  info_density: number;
  standalone_coherence: number;
  shareability: number;
  curiosity_gap: number;
  optimal_duration: number;
}

export interface WordTimestamp {
  id?: string;
  word: string;
  start_time: number;
  end_time: number;
  confidence?: number;
  word_index: number;
}

export interface ClipCaption {
  id?: string;
  preset_name: string;
  font_family: string;
  font_size: number;
  primary_color: string;
  highlight_color: string;
  stroke_color: string;
  stroke_width: number;
  position: "top" | "center" | "bottom";
  custom_words_json?: WordTimestamp[];
}

export interface GeneratedClip {
  id: string;
  video_id: string;
  title: string;
  summary?: string;
  hook_text?: string;
  topic_tag: string;
  start_time: number;
  end_time: number;
  duration_seconds: number;
  engagement_score: number;
  score_breakdown: ScoreBreakdown;
  aspect_ratio: string;
  storage_key?: string;
  thumbnail_key?: string;
  status: ClipStatus;
  captions?: ClipCaption;
  video_source_url?: string;
  created_at: string;
}

export interface ProcessingJob {
  id: string;
  video_id: string;
  stage: JobStage;
  progress_percent: number;
  stage_description: string;
  error_code?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface Video {
  id: string;
  user_id: string;
  title: string;
  original_filename: string;
  file_size_bytes: number;
  duration_seconds?: number;
  width?: number;
  height?: number;
  fps?: number;
  codec?: string;
  status: VideoStatus;
  thumbnail_key?: string;
  created_at: string;
  updated_at?: string;
  active_job?: ProcessingJob;
  clip_count?: number;
}

export interface CaptionPreset {
  id: string;
  name: string;
  description: string;
  font_family: string;
  font_size: number;
  primary_color: string;
  highlight_color: string;
  stroke_color: string;
  stroke_width: number;
  position: "top" | "center" | "bottom";
  uppercase: boolean;
  words_per_group: number;
}

export interface ExportItem {
  id: string;
  clip_id: string;
  export_format: string;
  resolution: string;
  file_size_bytes: number;
  download_url?: string;
  created_at: string;
}
