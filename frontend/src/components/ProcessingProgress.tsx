"use client";

import React from "react";
import { CheckIcon, SparklesIcon } from "./Icons";
import { JobStage, ProcessingJob } from "@/types";

interface ProcessingProgressProps {
  job?: ProcessingJob;
  onRefresh?: () => void;
}

const PIPELINE_STAGES: { stage: JobStage; label: string; desc: string }[] = [
  { stage: "EXTRACTING_AUDIO", label: "Audio & Stream Probe", desc: "Extracting 16kHz audio track" },
  { stage: "TRANSCRIBING", label: "Whisper Transcription", desc: "Generating word timestamps" },
  { stage: "ANALYZING_SEMANTICS", label: "AI Virality Analysis", desc: "Evaluating 7-factor virality matrix" },
  { stage: "RANKING_CLIPS", label: "Clip & Subtitle Generation", desc: "Rendering vertical framing" },
];

export const ProcessingProgress: React.FC<ProcessingProgressProps> = ({ job }) => {
  if (!job) return null;

  const getStageIndex = (stage: JobStage): number => {
    switch (stage) {
      case "QUEUED": return 0;
      case "EXTRACTING_AUDIO": return 0;
      case "TRANSCRIBING": return 1;
      case "ANALYZING_SEMANTICS": return 2;
      case "RANKING_CLIPS": return 3;
      case "CROPPING_RENDERING": return 3;
      case "COMPLETED": return 4;
      default: return 0;
    }
  };

  const currentIdx = getStageIndex(job.stage);
  const isFailed = job.stage === "FAILED";
  const isCompleted = job.stage === "COMPLETED";

  return (
    <div className="glass-panel-glow bg-[#10121c] p-6 rounded-2xl border border-purple-500/20 shadow-2xl mb-8">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
            <SparklesIcon className={`w-5 h-5 ${!isCompleted && !isFailed ? "animate-spin" : ""}`} />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>AI Pipeline Processing</span>
              {isCompleted ? (
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  Ready
                </span>
              ) : isFailed ? (
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
                  Failed
                </span>
              ) : (
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 animate-pulse border border-purple-500/30">
                  Live
                </span>
              )}
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">{job.stage_description || "Processing video content..."}</p>
          </div>
        </div>

        <div className="text-right">
          <span className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-cyan-400 font-mono">
            {job.progress_percent}%
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-white/5 h-2.5 rounded-full overflow-hidden mb-6 p-[2px] border border-white/5">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isFailed
              ? "bg-red-500"
              : "bg-gradient-to-r from-purple-500 via-indigo-500 to-cyan-400"
          }`}
          style={{ width: `${Math.max(5, job.progress_percent)}%` }}
        />
      </div>

      {/* Multi-stage Stepper */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        {PIPELINE_STAGES.map((s, idx) => {
          const isDone = currentIdx > idx || isCompleted;
          const isCurrent = currentIdx === idx && !isCompleted && !isFailed;

          return (
            <div
              key={s.stage}
              className={`p-3.5 rounded-xl border transition-all ${
                isCurrent
                  ? "bg-purple-500/10 border-purple-500/40 shadow-lg shadow-purple-500/10"
                  : isDone
                  ? "bg-emerald-500/5 border-emerald-500/20 text-zinc-300"
                  : "bg-white/[0.02] border-white/5 opacity-50"
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <div
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                    isDone
                      ? "bg-emerald-500 text-black"
                      : isCurrent
                      ? "bg-purple-500 text-white animate-pulse"
                      : "bg-white/10 text-zinc-400"
                  }`}
                >
                  {isDone ? <CheckIcon className="w-3 h-3 text-black" /> : idx + 1}
                </div>
                <span className={`text-xs font-semibold ${isCurrent ? "text-purple-300" : isDone ? "text-emerald-300" : "text-zinc-400"}`}>
                  {s.label}
                </span>
              </div>
              <p className="text-[11px] text-zinc-500">{s.desc}</p>
            </div>
          );
        })}
      </div>

      {isFailed && job.error_message && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-300">
          <span className="font-semibold">Error: </span>
          {job.error_message}
        </div>
      )}
    </div>
  );
};
