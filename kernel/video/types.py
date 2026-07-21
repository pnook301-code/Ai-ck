"""Video analysis types"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import time
import uuid


class VideoSourceType(Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    LOCAL = "local"
    URL = "url"


@dataclass
class FrameInfo:
    index: int
    timestamp_sec: float
    timestamp_str: str
    path: str
    width: int = 0
    height: int = 0
    scene_score: float = 0.0


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    confidence: float = 0.0
    language: str = ""


@dataclass
class Transcript:
    segments: List[TranscriptSegment] = field(default_factory=list)
    full_text: str = ""
    language: str = ""
    duration_sec: float = 0.0

    def text_around(self, timestamp_sec: float, window: float = 5.0) -> str:
        matching = []
        for seg in self.segments:
            if abs(seg.start - timestamp_sec) <= window:
                matching.append(f"[{self._fmt(seg.start)}-{self._fmt(seg.end)}] {seg.text}")
        return "\n".join(matching) if matching else ""

    def _fmt(self, sec: float) -> str:
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"


@dataclass
class VideoMeta:
    title: str = ""
    duration_sec: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    source_url: str = ""
    source_type: VideoSourceType = VideoSourceType.URL
    format: str = ""


@dataclass
class VideoAnalysisResult:
    id: str = field(default_factory=lambda: f"va_{uuid.uuid4().hex[:12]}")
    query: str = ""
    answer: str = ""
    frames: List[FrameInfo] = field(default_factory=list)
    transcript: Optional[Transcript] = None
    meta: Optional[VideoMeta] = None
    total_frames_in_video: int = 0
    keyframes_extracted: int = 0
    processing_time_sec: float = 0.0
    model: str = ""
    tokens_used: int = 0
    cost_estimate: float = 0.0
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "frames": self.keyframes_extracted,
            "total_frames": self.total_frames_in_video,
            "transcript_segments": len(self.transcript.segments) if self.transcript else 0,
            "duration_sec": self.meta.duration_sec if self.meta else 0,
            "processing_time_sec": round(self.processing_time_sec, 2),
            "error": self.error,
        }
