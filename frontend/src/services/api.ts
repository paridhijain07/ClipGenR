import {
  CaptionPreset,
  ClipCaption,
  ExportItem,
  GeneratedClip,
  ProcessingJob,
  Video,
  WordTimestamp,
} from "@/types";

const getApiBase = () => {
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
};

export async function fetchVideos(): Promise<Video[]> {
  try {
    const res = await fetch(`${getApiBase()}/videos`, { cache: "no-store" });
    if (!res.ok) {
      console.warn("Failed to fetch videos from API, status:", res.status);
      return [];
    }
    return res.json();
  } catch (err) {
    console.error("fetchVideos network error:", err);
    return [];
  }
}

export async function fetchVideoDetail(videoId: string): Promise<Video> {
  const res = await fetch(`${getApiBase()}/videos/${videoId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch video detail");
  return res.json();
}

export async function fetchVideoStatus(videoId: string): Promise<ProcessingJob> {
  const res = await fetch(`${getApiBase()}/videos/${videoId}/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch processing status");
  return res.json();
}

export async function triggerProcessing(videoId: string): Promise<ProcessingJob> {
  const res = await fetch(`${getApiBase()}/videos/${videoId}/process`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to trigger video processing");
  return res.json();
}

export async function uploadVideoWithProgress(
  file: File,
  title?: string,
  onProgress?: (percent: number) => void
): Promise<Video> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);
    formData.append("auto_process", "true");

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        const percent = Math.round((e.loaded / e.total) * 100);
        onProgress(percent);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const parsed = JSON.parse(xhr.responseText);
          resolve(parsed);
        } catch {
          reject(new Error("Invalid JSON response from server"));
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail || "Upload failed"));
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
    xhr.open("POST", `${getApiBase()}/videos/upload`);
    xhr.send(formData);
  });
}

export async function deleteVideo(videoId: string): Promise<void> {
  const res = await fetch(`${getApiBase()}/videos/${videoId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete video");
}

export async function fetchVideoClips(videoId: string): Promise<GeneratedClip[]> {
  try {
    const res = await fetch(`${getApiBase()}/clips/video/${videoId}`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch (err) {
    console.error("fetchVideoClips network error:", err);
    return [];
  }
}

export async function fetchClipDetail(clipId: string): Promise<GeneratedClip> {
  const res = await fetch(`${getApiBase()}/clips/${clipId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch clip detail");
  return res.json();
}

export async function fetchClipWords(clipId: string): Promise<WordTimestamp[]> {
  try {
    const res = await fetch(`${getApiBase()}/clips/${clipId}/words`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function updateClip(
  clipId: string,
  data: Partial<GeneratedClip>
): Promise<GeneratedClip> {
  const res = await fetch(`${getApiBase()}/clips/${clipId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update clip");
  return res.json();
}

export async function updateClipCaptions(
  clipId: string,
  data: Partial<ClipCaption>
): Promise<ClipCaption> {
  const res = await fetch(`${getApiBase()}/clips/${clipId}/captions`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update clip captions");
  return res.json();
}

export async function exportClip(clipId: string): Promise<ExportItem> {
  const res = await fetch(`${getApiBase()}/clips/${clipId}/export`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to export clip");
  return res.json();
}

export async function fetchCaptionPresets(): Promise<CaptionPreset[]> {
  try {
    const res = await fetch(`${getApiBase()}/presets`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export function getMediaUrl(storageKey?: string): string {
  if (!storageKey) return "";
  return `${getApiBase()}/videos/stream/${storageKey}`;
}
