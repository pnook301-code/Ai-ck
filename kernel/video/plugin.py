"""Video analysis plugin — /watch command interface"""

import os
from typing import Any, Dict, Optional

from .types import VideoSourceType, VideoAnalysisResult
from .analyzer import VideoAnalyzer


class WatchPlugin:
    def __init__(self, analyzer: Optional[VideoAnalyzer] = None):
        self._analyzer = analyzer or VideoAnalyzer()

    @property
    def name(self) -> str:
        return "watch"

    @property
    def description(self) -> str:
        return "Analyze a video by extracting keyframes and transcript, then answer questions about it."

    @property
    def commands(self) -> list[Dict[str, Any]]:
        return [
            {
                "name": "watch",
                "description": "Watch a video and answer questions about its content",
                "usage": "/watch <video_url_or_path> [your question]",
                "example": "/watch https://youtube.com/watch?v=abc123 What is the main point of this video?",
            }
        ]

    def parse(self, input_text: str) -> Optional[Dict[str, Any]]:
        if not input_text.startswith("/watch"):
            return None

        rest = input_text[len("/watch"):].strip()
        parts = rest.split(None, 1)
        if not parts:
            return None

        source = parts[0]
        query = parts[1] if len(parts) > 1 else "Summarize this video"

        source_type = self._detect_source_type(source)
        return {
            "source": source,
            "source_type": source_type,
            "query": query,
        }

    def execute(self, params: Dict[str, Any],
                llm_callback=None) -> VideoAnalysisResult:
        return self._analyzer.analyze(
            source=params["source"],
            query=params.get("query", "Summarize this video"),
            source_type=params.get("source_type", VideoSourceType.URL),
            time_start=params.get("time_start"),
            time_end=params.get("time_end"),
            max_frames=params.get("max_frames", 200),
            llm_callback=llm_callback,
        )

    def _detect_source_type(self, source: str) -> VideoSourceType:
        if os.path.exists(source):
            return VideoSourceType.LOCAL
        source_lower = source.lower()
        if "youtube.com" in source_lower or "youtu.be" in source_lower:
            return VideoSourceType.YOUTUBE
        if "tiktok.com" in source_lower:
            return VideoSourceType.TIKTOK
        if "instagram.com" in source_lower:
            return VideoSourceType.INSTAGRAM
        if source.startswith(("http://", "https://")):
            return VideoSourceType.URL
        return VideoSourceType.LOCAL
