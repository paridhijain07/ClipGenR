"use client";

import React, { useState } from "react";
import { DownloadIcon, FlameIcon, SlidersIcon, SparklesIcon } from "./Icons";
import { GeneratedClip } from "@/types";

interface ClipsListProps {
  clips: GeneratedClip[];
  onOpenStudio: (clip: GeneratedClip) => void;
  onQuickExport: (clip: GeneratedClip) => void;
}

export const ClipsList: React.FC<ClipsListProps> = ({
  clips,
  onOpenStudio,
  onQuickExport,
}) => {
  const [selectedScoreClip, setSelectedScoreClip] = useState<GeneratedClip | null>(null);

  if (clips.length === 0) {
    return (
      <div className="glass-panel p-12 rounded-2xl text-center border border-white/5 my-6">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-purple-500/10 flex items-center justify-center text-purple-400 mb-4">
          <SparklesIcon className="w-7 h-7" />
        </div>
        <h4 className="text-base font-bold text-white mb-1">No Viral Clips Generated Yet</h4>
        <p className="text-xs text-zinc-400 max-w-md mx-auto">
          Upload a long-form video above to automatically extract high-retention 9:16 shorts with animated karaoke subtitles.
        </p>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return "from-amber-400 to-yellow-500 text-amber-300 border-amber-500/30 bg-amber-500/10";
    if (score >= 80) return "from-emerald-400 to-teal-500 text-emerald-300 border-emerald-500/30 bg-emerald-500/10";
    return "from-purple-400 to-indigo-500 text-purple-300 border-purple-500/30 bg-purple-500/10";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <FlameIcon className="w-6 h-6 text-amber-400" />
            <span>AI Discovered Viral Clips</span>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
              {clips.length} Extracted
            </span>
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Ranked by multi-factor virality score, hook intensity, and audience retention modeling
          </p>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {clips.map((clip) => {
          const score = Math.round(clip.engagement_score);

          return (
            <div
              key={clip.id}
              className="glass-panel group relative rounded-2xl border border-white/10 hover:border-purple-500/40 bg-[#12131e]/90 p-5 transition-all duration-300 hover:shadow-xl hover:shadow-purple-500/10 flex flex-col justify-between"
            >
              {/* Card Header */}
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  {/* Topic badge */}
                  <span className="text-[11px] font-semibold tracking-wide uppercase px-2.5 py-1 rounded-lg bg-white/5 text-zinc-300 border border-white/5">
                    {clip.topic_tag}
                  </span>

                  {/* Viral Score Badge */}
                  <div
                    onClick={() => setSelectedScoreClip(selectedScoreClip?.id === clip.id ? null : clip)}
                    className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold cursor-pointer transition-all hover:scale-105 ${getScoreColor(
                      score
                    )}`}
                    title="Click to view 7-Factor Score Breakdown"
                  >
                    <FlameIcon className="w-3.5 h-3.5" />
                    <span>{score} Viral Score</span>
                  </div>
                </div>

                {/* Title */}
                <h3 className="font-bold text-base text-white line-clamp-2 leading-snug group-hover:text-purple-300 transition-colors">
                  {clip.title}
                </h3>

                {/* Hook quote */}
                {clip.hook_text && (
                  <div className="mt-3 p-2.5 rounded-xl bg-black/40 border border-white/5 text-xs text-zinc-300 italic">
                    <span className="text-purple-400 font-bold not-italic mr-1">Hook:</span>
                    &ldquo;{clip.hook_text}&rdquo;
                  </div>
                )}

                {/* Duration & Timestamps */}
                <div className="flex items-center gap-3 mt-4 text-xs text-zinc-400">
                  <span className="font-mono bg-white/5 px-2 py-0.5 rounded text-zinc-300">
                    {Math.floor(clip.start_time / 60)}:{(Math.floor(clip.start_time) % 60).toString().padStart(2, "0")} -{" "}
                    {Math.floor(clip.end_time / 60)}:{(Math.floor(clip.end_time) % 60).toString().padStart(2, "0")}
                  </span>
                  <span>•</span>
                  <span>{clip.duration_seconds.toFixed(0)}s duration</span>
                  <span>•</span>
                  <span className="text-emerald-400 font-medium">9:16 Vertical</span>
                </div>
              </div>

              {/* 7-Factor Virality Popover */}
              {selectedScoreClip?.id === clip.id && clip.score_breakdown && (
                <div className="mt-4 p-3.5 rounded-xl bg-[#0b0c13] border border-amber-500/30 text-xs space-y-2 animate-in fade-in duration-200">
                  <div className="flex items-center justify-between pb-1 border-b border-white/5 font-semibold text-amber-300">
                    <span>7-Factor Virality Analysis</span>
                    <span>Score</span>
                  </div>
                  <div className="space-y-1.5 text-zinc-400">
                    <div className="flex justify-between">
                      <span>Opening Hook Strength:</span>
                      <span className="text-white font-mono">{clip.score_breakdown.hook_strength}/100</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Emotional & Energy Spikes:</span>
                      <span className="text-white font-mono">{clip.score_breakdown.emotional_resonance}/100</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Information Density:</span>
                      <span className="text-white font-mono">{clip.score_breakdown.info_density}/100</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Standalone Coherence:</span>
                      <span className="text-white font-mono">{clip.score_breakdown.standalone_coherence}/100</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Shareability & Relatability:</span>
                      <span className="text-white font-mono">{clip.score_breakdown.shareability}/100</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Curiosity Loop & Retention:</span>
                      <span className="text-white font-mono">{clip.score_breakdown.curiosity_gap}/100</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2.5 mt-5 pt-4 border-t border-white/5">
                <button
                  onClick={() => onOpenStudio(clip)}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-300 hover:text-white font-medium text-xs transition-all cursor-pointer"
                >
                  <SlidersIcon className="w-3.5 h-3.5" />
                  <span>Open Studio</span>
                </button>
                <button
                  onClick={() => onQuickExport(clip)}
                  className="flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-md shadow-purple-600/20 transition-all cursor-pointer"
                  title="Render and download 9:16 video with burned captions"
                >
                  <DownloadIcon className="w-3.5 h-3.5" />
                  <span>Export</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
