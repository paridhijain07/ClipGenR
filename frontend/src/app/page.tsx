"use client";

import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { UploadModal } from "@/components/UploadModal";
import { ProcessingProgress } from "@/components/ProcessingProgress";
import { ClipsList } from "@/components/ClipsList";
import { ClipEditorModal } from "@/components/ClipEditorModal";
import {
  RefreshIcon,
  SparklesIcon,
  TrashIcon,
  UploadCloudIcon,
  VideoIcon,
} from "@/components/Icons";
import {
  deleteVideo,
  exportClip,
  fetchVideoClips,
  fetchVideos,
  fetchVideoStatus,
} from "@/services/api";
import { GeneratedClip, Video } from "@/types";

export default function HomePage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const [clips, setClips] = useState<GeneratedClip[]>([]);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [editingClip, setEditingClip] = useState<GeneratedClip | null>(null);
  const [isStudioOpen, setIsStudioOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Manual refresh helper
  const handleRefreshVideos = () => {
    fetchVideos()
      .then((vids) => {
        setVideos(vids);
        setSelectedVideo((current) => {
          if (!current && vids.length > 0) return vids[0];
          if (current && !vids.find((v) => v.id === current.id)) {
            return vids.length > 0 ? vids[0] : null;
          }
          return current;
        });
      })
      .catch((e) => console.error("Failed to load videos:", e));
  };

  // Load initial videos on mount
  useEffect(() => {
    let isMounted = true;
    fetchVideos()
      .then((vids) => {
        if (!isMounted) return;
        setVideos(vids);
        setSelectedVideo((current) => {
          if (!current && vids.length > 0) return vids[0];
          if (current && !vids.find((v) => v.id === current.id)) {
            return vids.length > 0 ? vids[0] : null;
          }
          return current;
        });
      })
      .catch((e) => console.error("Failed to load videos:", e))
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Load clips when selected video changes
  useEffect(() => {
    if (!selectedVideo) return;

    let isMounted = true;
    fetchVideoClips(selectedVideo.id)
      .then((c) => {
        if (isMounted) setClips(c);
      })
      .catch((e) => console.error("Failed to load clips:", e));

    return () => {
      isMounted = false;
    };
  }, [selectedVideo]);

  // Polling for active processing jobs
  useEffect(() => {
    if (!selectedVideo) return;
    const isProcessing =
      selectedVideo.status === "PROCESSING" ||
      selectedVideo.status === "PENDING" ||
      (selectedVideo.active_job &&
        selectedVideo.active_job.stage !== "COMPLETED" &&
        selectedVideo.active_job.stage !== "FAILED");

    if (!isProcessing) return;

    const interval = setInterval(() => {
      fetchVideoStatus(selectedVideo.id)
        .then((job) => {
          setSelectedVideo((prev) => (prev ? { ...prev, active_job: job } : null));

          if (job.stage === "COMPLETED" || job.stage === "FAILED") {
            clearInterval(interval);
            handleRefreshVideos();
            fetchVideoClips(selectedVideo.id)
              .then(setClips)
              .catch(() => {});
          }
        })
        .catch((e) => console.error("Status poll error:", e));
    }, 2000);

    return () => clearInterval(interval);
  }, [selectedVideo]);

  const handleUploadSuccess = (newVideo: Video) => {
    setVideos((prev) => [newVideo, ...prev]);
    setSelectedVideo(newVideo);
  };

  const handleDeleteVideo = async (videoId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this video and its generated clips?")) return;
    try {
      await deleteVideo(videoId);
      setVideos((prev) => prev.filter((v) => v.id !== videoId));
      if (selectedVideo?.id === videoId) {
        const remaining = videos.filter((v) => v.id !== videoId);
        setSelectedVideo(remaining.length > 0 ? remaining[0] : null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete video";
      alert(msg);
    }
  };

  const handleOpenStudio = (clip: GeneratedClip) => {
    setEditingClip(clip);
    setIsStudioOpen(true);
  };

  const handleQuickExport = async (clip: GeneratedClip) => {
    try {
      const exp = await exportClip(clip.id);
      window.open(`http://localhost:8000${exp.download_url}`, "_blank");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Export failed";
      alert(msg);
    }
  };

  return (
    <div className="min-h-screen bg-[#090a10] text-slate-100 flex flex-col selection:bg-purple-500 selection:text-white">
      {/* Top Navigation */}
      <Navbar onOpenUpload={() => setIsUploadOpen(true)} videoCount={videos.length} />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Banner when no videos exist */}
        {videos.length === 0 && !isLoading && (
          <div className="relative rounded-3xl overflow-hidden glass-panel-glow border border-purple-500/20 p-8 sm:p-12 mb-10 text-center bg-gradient-to-b from-[#161828] to-[#0d0e17]">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/20 border border-purple-500/30 text-purple-300 text-xs font-semibold mb-4">
              <SparklesIcon className="w-3.5 h-3.5" />
              <span>Next-Gen AI Video Repurposing</span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white max-w-2xl mx-auto leading-tight mb-4">
              Turn 1 Long Video Into <span className="text-gradient">10 Viral Shorts</span> in Seconds
            </h1>

            <p className="text-sm sm:text-base text-zinc-400 max-w-xl mx-auto mb-8">
              ClipGenR automatically transcribes, identifies viral hooks with 7-factor virality scoring, reframes to 9:16 vertical, and generates dynamic karaoke captions.
            </p>

            <button
              onClick={() => setIsUploadOpen(true)}
              className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-2xl bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-500 hover:from-purple-500 hover:to-cyan-400 text-white font-bold text-base shadow-xl shadow-purple-600/30 transition-all hover:scale-105 active:scale-95 cursor-pointer"
            >
              <UploadCloudIcon className="w-5 h-5" />
              <span>Upload Video & Extract Shorts</span>
            </button>
          </div>
        )}

        {/* Video Projects Tabs (if videos exist) */}
        {videos.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-zinc-400 uppercase tracking-wider">Your Video Projects</h3>
              <button
                onClick={handleRefreshVideos}
                className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors"
              >
                <RefreshIcon className="w-3.5 h-3.5" />
                <span>Refresh</span>
              </button>
            </div>

            <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin">
              {videos.map((v) => {
                const isSelected = selectedVideo?.id === v.id;
                return (
                  <div
                    key={v.id}
                    onClick={() => setSelectedVideo(v)}
                    className={`flex-shrink-0 w-64 p-3.5 rounded-2xl border cursor-pointer transition-all flex flex-col justify-between group ${
                      isSelected
                        ? "bg-purple-600/15 border-purple-500 shadow-lg shadow-purple-500/10"
                        : "bg-white/[0.02] border-white/10 hover:border-white/20"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center text-purple-400">
                          <VideoIcon className="w-4 h-4" />
                        </div>
                        <button
                          onClick={(e) => handleDeleteVideo(v.id, e)}
                          className="opacity-0 group-hover:opacity-100 p-1 text-zinc-500 hover:text-red-400 transition-opacity"
                          title="Delete Video"
                        >
                          <TrashIcon className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <h4 className="font-bold text-xs text-white line-clamp-1 group-hover:text-purple-300 transition-colors">
                        {v.title}
                      </h4>
                    </div>

                    <div className="flex items-center justify-between mt-3 text-[11px] text-zinc-400">
                      <span>{v.clip_count || 0} Clips</span>
                      <span
                        className={`font-semibold capitalize ${
                          v.status === "COMPLETED"
                            ? "text-emerald-400"
                            : v.status === "PROCESSING"
                            ? "text-purple-400 animate-pulse"
                            : "text-zinc-400"
                        }`}
                      >
                        {v.status.toLowerCase()}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Live Processing Pipeline Stepper */}
        {selectedVideo?.active_job && selectedVideo.active_job.stage !== "COMPLETED" && (
          <ProcessingProgress job={selectedVideo.active_job} />
        )}

        {/* AI Discovered Clips */}
        {selectedVideo && (
          <ClipsList
            clips={clips}
            onOpenStudio={handleOpenStudio}
            onQuickExport={handleQuickExport}
          />
        )}
      </main>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

      {/* Interactive Studio Modal */}
      <ClipEditorModal
        clip={editingClip}
        isOpen={isStudioOpen}
        onClose={() => setIsStudioOpen(false)}
      />
    </div>
  );
}
