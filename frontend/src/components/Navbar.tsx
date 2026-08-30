import React from "react";
import { SparklesIcon, UploadCloudIcon, VideoIcon } from "./Icons";

interface NavbarProps {
  onOpenUpload: () => void;
  videoCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenUpload, videoCount }) => {
  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-white/5 bg-[#090a0f]/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-500 to-cyan-400 p-[1px] shadow-lg shadow-purple-500/20">
            <div className="w-full h-full bg-[#0d0e15] rounded-xl flex items-center justify-center">
              <SparklesIcon className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white">ClipGenR</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-semibold border border-purple-500/30">
                AI 2.0
              </span>
            </div>
            <p className="text-[11px] text-zinc-400 hidden sm:block">Automated Viral Shorts & Reels Generator</p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="hidden md:flex items-center gap-2 text-xs text-zinc-400 bg-white/5 px-3 py-1.5 rounded-lg border border-white/5">
            <VideoIcon className="w-3.5 h-3.5 text-purple-400" />
            <span>{videoCount} {videoCount === 1 ? "Project" : "Projects"}</span>
          </div>

          <button
            onClick={onOpenUpload}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium text-sm shadow-lg shadow-purple-600/25 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
          >
            <UploadCloudIcon className="w-4 h-4" />
            <span>Upload Long Video</span>
          </button>
        </div>
      </div>
    </header>
  );
};
