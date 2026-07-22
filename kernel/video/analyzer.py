"""VideoAnalyzer — orchestrates frame extraction, transcription, and AI analysis"""

import time
from typing import List, Optional

from .types import (
    VideoAnalysisResult, VideoMeta, VideoSourceType,
    FrameInfo, Transcript,
)
from .frame_extractor import VideoFrameExtractor
from .transcriber import AudioTranscriber


class VideoAnalyzer:
    def __init__(self, frame_extractor: Optional[VideoFrameExtractor] = None,
                 transcriber: Optional[AudioTranscriber] = None,
                 llm_callback=None):
        self._frame_extractor = frame_extractor or VideoFrameExtractor()
        self._transcriber = transcriber or AudioTranscriber()
        self._llm_callback = llm_callback

    def analyze(self, source: str,
                query: str = "",
                source_type: VideoSourceType = VideoSourceType.URL,
                time_start: Optional[float] = None,
                time_end: Optional[float] = None,
                max_frames: int = 200,
                model: str = "",
                llm_callback=None) -> VideoAnalysisResult:
        cb = llm_callback or self._llm_callback
        start_time = time.time()
        result = VideoAnalysisResult(query=query, model=model)

        try:
            frames, meta, video_path = self._frame_extractor.extract(
                source, source_type, time_start, time_end, max_frames,
            )
            result.frames = frames
            result.meta = meta
            result.keyframes_extracted = len(frames)
            result.total_frames_in_video = int(meta.duration_sec * meta.fps) if meta.fps else 0

            transcript = self._transcriber.transcribe(video_path, time_start=time_start, time_end=time_end)
            result.transcript = transcript

            if cb and query:
                answer = self._query_llm(query, frames, transcript, meta, cb)
                result.answer = answer

        except Exception as e:
            result.error = str(e)

        result.processing_time_sec = time.time() - start_time
        return result

    def _query_llm(self, query: str, frames: List[FrameInfo],
                   transcript: Transcript, meta: VideoMeta,
                   llm_callback) -> str:
        context_parts = [
            f"Video: {meta.title or 'untitled'}",
            f"Duration: {self._fmt_duration(meta.duration_sec)}",
            f"Keyframes captured: {len(frames)}",
        ]

        if transcript and transcript.segments:
            context_parts.append(f"\nTranscript ({len(transcript.segments)} segments):")
            for seg in transcript.segments[:100]:
                ts = self._fmt_ts(seg.start)
                context_parts.append(f"[{ts}] {seg.text}")

        if frames:
            context_parts.append(f"\nKeyframes extracted: {len(frames)} frames at scene changes.")
            context_parts.append("Frame sequence (visual content changes detected at these timestamps):")
            for f in frames:
                context_parts.append(f"  [{f.timestamp_str}] {f.path}")

        full_context = "\n".join(context_parts)

        prompt = f"""You are analyzing a video to answer the user's question.

VIDEO METADATA:
{full_context}

USER QUESTION: {query}

Instructions:
- Use both the transcript text and the visual keyframes to answer.
- If keyframes show visual information not in the transcript, describe what you see.
- Be specific about timestamps when referencing events in the video.
- Provide a thorough, accurate answer based on what the video actually contains.
"""

        return llm_callback(prompt, frames=frames)

    def _fmt_duration(self, sec: float) -> str:
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"

    def _fmt_ts(self, sec: float) -> str:
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def cleanup(self):
        self._frame_extractor.cleanup()
