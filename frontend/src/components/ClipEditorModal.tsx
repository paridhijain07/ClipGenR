"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  CheckIcon,
  DownloadIcon,
  PauseIcon,
  PlayIcon,
  SlidersIcon,
  SparklesIcon,
  TypeIcon,
  XIcon,
} from "./Icons";
import { exportClip, fetchCaptionPresets, fetchClipWords, updateClipCaptions } from "@/services/api";
import { CaptionPreset, ExportItem, GeneratedClip, WordTimestamp } from "@/types";

interface ClipEditorModalProps {
  clip: GeneratedClip | null;
  isOpen: boolean;
  onClose: () => void;
}

// Client-side quick Devanagari to Hinglish mapping for live preview
function toHinglishText(text: string): string {
  const map: Record<string, string> = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "अं": "an", "अः": "ah",
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ं": "n", "ः": "h", "्": "",
    "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f"
  };

  let out = "";
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    out += map[char] !== undefined ? map[char] : char;
  }
  return out;
}

export const ClipEditorModal: React.FC<ClipEditorModalProps> = ({
  clip,
  isOpen,
  onClose,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(clip?.start_time || 0);
  const [words, setWords] = useState<WordTimestamp[]>([]);
  const [presets, setPresets] = useState<CaptionPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>(
    clip?.captions?.preset_name || "hormozi_yellow"
  );
  const [isHinglish, setIsHinglish] = useState(true);
  
  // Custom caption overrides
  const [fontSize, setFontSize] = useState(clip?.captions?.font_size || 42);
  const [highlightColor, setHighlightColor] = useState(clip?.captions?.highlight_color || "#FACC15");
  const [primaryColor, setPrimaryColor] = useState(clip?.captions?.primary_color || "#FFFFFF");
  const [position, setPosition] = useState<"top" | "center" | "bottom">(
    clip?.captions?.position || "bottom"
  );

  // Export State
  const [isExporting, setIsExporting] = useState(false);
  const [exportedItem, setExportedItem] = useState<ExportItem | null>(null);
  const [activeTab, setActiveTab] = useState<"style" | "transcript">("style");

  useEffect(() => {
    if (!clip || !isOpen) return;

    let isMounted = true;
    fetchCaptionPresets().then((p) => {
      if (isMounted) setPresets(p);
    }).catch(() => {});

    fetchClipWords(clip.id).then((w) => {
      if (isMounted) setWords(w);
    }).catch(() => {});

    return () => {
      isMounted = false;
    };
  }, [clip, isOpen]);

  if (!isOpen || !clip) return null;

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      if (videoRef.current.currentTime < clip.start_time || videoRef.current.currentTime >= clip.end_time) {
        videoRef.current.currentTime = clip.start_time;
      }
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const t = videoRef.current.currentTime;
    setCurrentTime(t);

    if (t >= clip.end_time) {
      videoRef.current.currentTime = clip.start_time;
      videoRef.current.play();
    }
  };

  const handlePresetSelect = async (presetId: string) => {
    setSelectedPreset(presetId);
    const p = presets.find((x) => x.id === presetId);
    if (p) {
      setFontSize(p.font_size);
      setHighlightColor(p.highlight_color);
      setPrimaryColor(p.primary_color);
      setPosition(p.position);

      await updateClipCaptions(clip.id, {
        preset_name: presetId,
        font_size: p.font_size,
        primary_color: p.primary_color,
        highlight_color: p.highlight_color,
        position: p.position,
      });
    }
  };

  const handleExport = async () => {
    try {
      setIsExporting(true);
      const res = await exportClip(clip.id);
      setExportedItem(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Export failed";
      alert(msg);
    } finally {
      setIsExporting(false);
    }
  };

  // Find active words for live subtitle overlay
  const activeWord = words.find((w) => currentTime >= w.start_time && currentTime <= w.end_time);
  const activeIndex = words.findIndex((w) => currentTime >= w.start_time && currentTime <= w.end_time);
  
  const activeChunk = activeIndex >= 0
    ? words.slice(Math.max(0, activeIndex - 1), Math.min(words.length, activeIndex + 3))
    : words.filter((w) => Math.abs(w.start_time - currentTime) < 1.2).slice(0, 3);

  const getPositionClass = () => {
    switch (position) {
      case "top": return "top-12";
      case "center": return "top-1/2 -translate-y-1/2";
      case "bottom": return "bottom-14";
      default: return "bottom-14";
    }
  };

  const formatWordDisplay = (w: string) => {
    return isHinglish ? toHinglishText(w) : w;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="w-full max-w-5xl h-[90vh] glass-panel-glow bg-[#0d0e17] rounded-3xl border border-white/10 flex flex-col overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-[#121422]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center">
              <SlidersIcon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white line-clamp-1">{clip.title}</h2>
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <span>{clip.duration_seconds.toFixed(0)}s Short</span>
                <span>•</span>
                <span className="text-amber-400 font-semibold">{Math.round(clip.engagement_score)}/100 Virality</span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleExport}
              disabled={isExporting}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-purple-600/30 transition-all cursor-pointer disabled:opacity-50"
            >
              {isExporting ? <SparklesIcon className="w-4 h-4 animate-spin" /> : <DownloadIcon className="w-4 h-4" />}
              <span>{isExporting ? "Rendering 9:16 Video..." : "Export Full HD"}</span>
            </button>

            <button
              onClick={onClose}
              className="text-zinc-400 hover:text-white p-2 rounded-xl hover:bg-white/5 transition-colors"
            >
              <XIcon className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Studio Workspace */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
          {/* Left: 9:16 Video Preview Stage (5 cols) */}
          <div className="lg:col-span-5 bg-black/60 flex flex-col items-center justify-center p-6 relative border-r border-white/5">
            {/* Phone Bezel Container (9:16 aspect ratio) */}
            <div className="relative w-[280px] h-[497px] rounded-3xl overflow-hidden shadow-2xl border-4 border-[#242636] bg-black group">
              <video
                ref={videoRef}
                src={clip.video_source_url}
                onTimeUpdate={handleTimeUpdate}
                onClick={togglePlay}
                playsInline
                className="w-full h-full object-cover cursor-pointer"
              />

              {/* Dynamic Live Karaoke Caption Overlay */}
              <div
                className={`absolute left-0 right-0 px-4 text-center pointer-events-none transition-all duration-150 ${getPositionClass()}`}
              >
                {activeChunk.length > 0 ? (
                  <div
                    className="font-black uppercase tracking-wider leading-tight drop-shadow-[0_4px_8px_rgba(0,0,0,0.9)]"
                    style={{
                      fontSize: `${Math.round(fontSize * 0.45)}px`,
                      fontFamily: "Nirmala UI, Impact, sans-serif",
                      WebkitTextStroke: "1.5px #000000",
                    }}
                  >
                    {activeChunk.map((w, i) => {
                      const isActive = activeWord && activeWord.word === w.word && activeWord.start_time === w.start_time;
                      const displayText = formatWordDisplay(w.word);
                      return (
                        <span
                          key={i}
                          className={`inline-block mx-1 transition-transform ${
                            isActive ? "active-karaoke-word" : ""
                          }`}
                          style={{
                            color: isActive ? highlightColor : primaryColor,
                            transform: isActive ? "scale(1.1)" : "scale(1.0)",
                          }}
                        >
                          {displayText}
                        </span>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-zinc-400 text-xs font-mono">
                    [Captions Active]
                  </div>
                )}
              </div>

              {/* Play Overlay Button */}
              {!isPlaying && (
                <div
                  onClick={togglePlay}
                  className="absolute inset-0 bg-black/40 flex items-center justify-center cursor-pointer transition-opacity"
                >
                  <div className="w-16 h-16 rounded-full bg-purple-600/90 text-white flex items-center justify-center shadow-xl hover:scale-110 transition-transform">
                    <PlayIcon className="w-7 h-7 ml-1" />
                  </div>
                </div>
              )}

              {/* Scrubbing Bar */}
              <div className="absolute bottom-2 left-3 right-3 flex items-center gap-2 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full text-[10px] text-white">
                <button onClick={togglePlay} className="hover:text-purple-400">
                  {isPlaying ? <PauseIcon className="w-3 h-3" /> : <PlayIcon className="w-3 h-3" />}
                </button>
                <span className="font-mono">{Math.max(0, currentTime - clip.start_time).toFixed(1)}s</span>
                <div className="flex-1 bg-white/20 h-1 rounded-full overflow-hidden">
                  <div
                    className="bg-purple-500 h-full"
                    style={{
                      width: `${Math.min(
                        100,
                        Math.max(0, ((currentTime - clip.start_time) / clip.duration_seconds) * 100)
                      )}%`,
                    }}
                  />
                </div>
                <span className="font-mono text-zinc-400">{clip.duration_seconds.toFixed(0)}s</span>
              </div>
            </div>
          </div>

          {/* Right: Studio Customizer Controls (7 cols) */}
          <div className="lg:col-span-7 flex flex-col overflow-y-auto p-6 bg-[#0f111c]">
            {/* Export Success Alert */}
            {exportedItem && (
              <div className="mb-6 p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between animate-in fade-in">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                    <CheckIcon className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-emerald-300">Render Completed!</h4>
                    <p className="text-[11px] text-zinc-400">1080x1920 60FPS vertical video ready for download.</p>
                  </div>
                </div>
                <a
                  href={`http://localhost:8000${exportedItem.download_url}`}
                  target="_blank"
                  rel="noreferrer"
                  download
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500 text-black font-bold text-xs hover:bg-emerald-400 transition-colors shadow-md"
                >
                  <DownloadIcon className="w-3.5 h-3.5" />
                  <span>Download MP4</span>
                </a>
              </div>
            )}

            {/* Tabs */}
            <div className="flex gap-2 p-1 rounded-xl bg-white/5 w-fit mb-6 border border-white/5">
              <button
                onClick={() => setActiveTab("style")}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === "style" ? "bg-purple-600 text-white shadow-md" : "text-zinc-400 hover:text-white"
                }`}
              >
                <TypeIcon className="w-3.5 h-3.5" />
                <span>Caption Presets & Styling</span>
              </button>
              <button
                onClick={() => setActiveTab("transcript")}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  activeTab === "transcript" ? "bg-purple-600 text-white shadow-md" : "text-zinc-400 hover:text-white"
                }`}
              >
                <SlidersIcon className="w-3.5 h-3.5" />
                <span>Word Transcript ({words.length})</span>
              </button>
            </div>

            {activeTab === "style" ? (
              <div className="space-y-6">
                {/* Language Script Toggle (Hinglish vs Pure Hindi) */}
                <div className="p-3.5 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
                      <span>Caption Language Script</span>
                      <span className="text-[10px] bg-purple-500/30 text-purple-300 px-2 py-0.5 rounded-full font-semibold">Viral Format</span>
                    </h4>
                    <p className="text-[11px] text-zinc-400 mt-0.5">Toggle between Latin English letters (Hinglish) or Devanagari (हिंदी)</p>
                  </div>
                  <div className="flex gap-1.5 bg-black/40 p-1 rounded-xl border border-white/10">
                    <button
                      onClick={() => setIsHinglish(true)}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                        isHinglish ? "bg-purple-600 text-white shadow-md" : "text-zinc-400 hover:text-white"
                      }`}
                    >
                      Hinglish (English script)
                    </button>
                    <button
                      onClick={() => setIsHinglish(false)}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                        !isHinglish ? "bg-purple-600 text-white shadow-md" : "text-zinc-400 hover:text-white"
                      }`}
                    >
                      हिंदी (Devanagari)
                    </button>
                  </div>
                </div>

                {/* Presets Grid */}
                <div>
                  <label className="block text-xs font-bold text-zinc-300 mb-3 uppercase tracking-wider">
                    Choose Viral Caption Preset
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {presets.map((p) => {
                      const isSelected = selectedPreset === p.id;
                      return (
                        <div
                          key={p.id}
                          onClick={() => handlePresetSelect(p.id)}
                          className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                            isSelected
                              ? "bg-purple-500/15 border-purple-500 shadow-lg shadow-purple-500/10"
                              : "bg-white/[0.02] border-white/10 hover:border-white/20"
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-bold text-xs text-white">{p.name}</span>
                            {isSelected && <CheckIcon className="w-3.5 h-3.5 text-purple-400" />}
                          </div>
                          <p className="text-[11px] text-zinc-400 line-clamp-2">{p.description}</p>
                          <div className="flex items-center gap-2 mt-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: p.highlight_color }} />
                            <span className="text-[10px] font-mono text-zinc-400">{p.highlight_color}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Custom Fine-Tuning */}
                <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 space-y-4">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">Style Fine-Tuning</h4>

                  {/* Position */}
                  <div>
                    <label className="block text-xs text-zinc-400 mb-1.5">Subtitle Position</label>
                    <div className="grid grid-cols-3 gap-2">
                      {(["top", "center", "bottom"] as const).map((pos) => (
                        <button
                          key={pos}
                          onClick={() => setPosition(pos)}
                          className={`py-1.5 rounded-lg text-xs font-medium capitalize border transition-all cursor-pointer ${
                            position === pos
                              ? "bg-purple-600/30 border-purple-500 text-white"
                              : "bg-white/5 border-white/5 text-zinc-400 hover:text-white"
                          }`}
                        >
                          {pos}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Highlight Color */}
                  <div>
                    <label className="block text-xs text-zinc-400 mb-1.5">Active Word Karaoke Color</label>
                    <div className="flex items-center gap-3">
                      {["#FACC15", "#38BDF8", "#22C55E", "#F43F5E", "#D946EF"].map((hex) => (
                        <div
                          key={hex}
                          onClick={() => setHighlightColor(hex)}
                          className={`w-7 h-7 rounded-full cursor-pointer transition-transform border-2 ${
                            highlightColor === hex ? "scale-125 border-white" : "border-transparent"
                          }`}
                          style={{ backgroundColor: hex }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider">Word-Level Timestamps</h4>
                  <span className="text-xs text-zinc-400">Click any word to jump video</span>
                </div>

                <div className="p-3 rounded-2xl bg-black/40 border border-white/5 max-h-[350px] overflow-y-auto flex flex-wrap gap-2">
                  {words.map((w, idx) => {
                    const isWordActive = currentTime >= w.start_time && currentTime <= w.end_time;
                    const wordText = formatWordDisplay(w.word);
                    return (
                      <button
                        key={idx}
                        onClick={() => {
                          if (videoRef.current) {
                            videoRef.current.currentTime = w.start_time;
                            videoRef.current.play();
                            setIsPlaying(true);
                          }
                        }}
                        className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer ${
                          isWordActive
                            ? "bg-amber-400 text-black font-bold scale-105"
                            : "bg-white/5 text-zinc-300 hover:bg-purple-600/30 hover:text-white"
                        }`}
                      >
                        {wordText}
                        <span className="text-[10px] text-zinc-500 ml-1">{(w.start_time - clip.start_time).toFixed(1)}s</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
