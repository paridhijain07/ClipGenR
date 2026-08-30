"use client";

import React, { useRef, useState } from "react";
import { SparklesIcon, UploadCloudIcon, VideoIcon, XIcon } from "./Icons";
import { uploadVideoWithProgress } from "@/services/api";
import { Video } from "@/types";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (video: Video) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      handleFileSelected(file);
    }
  };

  const handleFileSelected = (file: File) => {
    setErrorMsg(null);
    const validExtensions = [".mp4", ".mov", ".mkv", ".webm", ".avi"];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!validExtensions.includes(ext)) {
      setErrorMsg(`Unsupported file type (${ext}). Please select an MP4, MOV, MKV, or WEBM video.`);
      return;
    }

    setSelectedFile(file);
    if (!title) {
      const baseName = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
      setTitle(baseName);
    }
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile) return;

    try {
      setIsUploading(true);
      setErrorMsg(null);
      setUploadPercent(0);

      const video = await uploadVideoWithProgress(selectedFile, title, (pct) => {
        setUploadPercent(pct);
      });

      onUploadSuccess(video);
      onClose();
      // Reset state
      setSelectedFile(null);
      setTitle("");
      setUploadPercent(0);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to upload video";
      setErrorMsg(message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-xl glass-panel-glow bg-[#12141e] rounded-2xl border border-white/10 p-6 shadow-2xl relative">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center text-purple-400">
              <UploadCloudIcon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Upload Long-Form Video</h2>
              <p className="text-xs text-zinc-400">Transform full-length podcast, webinar, or video into viral clips</p>
            </div>
          </div>
          {!isUploading && (
            <button
              onClick={onClose}
              className="text-zinc-400 hover:text-white p-1.5 rounded-lg hover:bg-white/5 transition-colors"
            >
              <XIcon className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Dropzone */}
        <div className="mt-5 space-y-4">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleFileDrop}
            onClick={() => !isUploading && fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
              dragOver
                ? "border-purple-500 bg-purple-500/10 scale-[0.99]"
                : selectedFile
                ? "border-emerald-500/50 bg-emerald-500/5"
                : "border-white/10 hover:border-purple-500/50 hover:bg-white/[0.02]"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/quicktime,video/x-matroska,video/webm,video/x-msvideo"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFileSelected(e.target.files[0])}
              disabled={isUploading}
            />

            {selectedFile ? (
              <div className="flex flex-col items-center gap-2">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <VideoIcon className="w-6 h-6" />
                </div>
                <p className="text-sm font-semibold text-white truncate max-w-sm">{selectedFile.name}</p>
                <p className="text-xs text-zinc-400">{(selectedFile.size / (1024 * 1024)).toFixed(1)} MB • Click to replace</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center">
                  <UploadCloudIcon className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">Drag & drop your video here, or <span className="text-purple-400 underline">browse</span></p>
                  <p className="text-xs text-zinc-500 mt-1">Supports MP4, MOV, MKV, WEBM (Up to 2GB)</p>
                </div>
              </div>
            )}
          </div>

          {/* Title Input */}
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">Project Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Creator Masterclass Ep 14"
              disabled={isUploading}
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#0a0b10] border border-white/10 text-white text-sm focus:outline-none focus:border-purple-500 transition-colors"
            />
          </div>

          {/* Progress Bar */}
          {isUploading && (
            <div className="space-y-2 bg-purple-500/10 p-3.5 rounded-xl border border-purple-500/20">
              <div className="flex justify-between text-xs font-medium">
                <span className="text-purple-300 flex items-center gap-1.5">
                  <SparklesIcon className="w-3.5 h-3.5 animate-spin" />
                  Uploading video to processing pipeline...
                </span>
                <span className="text-white font-mono">{uploadPercent}%</span>
              </div>
              <div className="w-full bg-white/10 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-purple-500 to-cyan-400 h-full transition-all duration-200"
                  style={{ width: `${uploadPercent}%` }}
                />
              </div>
            </div>
          )}

          {/* Error Message */}
          {errorMsg && (
            <div className="text-xs text-red-400 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
              {errorMsg}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            {!isUploading && (
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
            )}
            <button
              type="button"
              onClick={handleUploadSubmit}
              disabled={!selectedFile || isUploading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm shadow-lg shadow-purple-600/30 transition-all cursor-pointer"
            >
              <SparklesIcon className="w-4 h-4" />
              <span>{isUploading ? "Uploading..." : "Generate AI Clips"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
