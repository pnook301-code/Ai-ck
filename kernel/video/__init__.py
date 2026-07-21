"""Video analysis module — watch videos, extract frames + transcript, answer questions"""

from .types import (
    VideoSourceType, FrameInfo, TranscriptSegment, Transcript,
    VideoMeta, VideoAnalysisResult,
)
from .scene_detector import SceneDetector
from .frame_extractor import VideoFrameExtractor
from .transcriber import AudioTranscriber
from .analyzer import VideoAnalyzer
from .plugin import WatchPlugin

__all__ = [
    "VideoSourceType",
    "FrameInfo",
    "TranscriptSegment",
    "Transcript",
    "VideoMeta",
    "VideoAnalysisResult",
    "SceneDetector",
    "VideoFrameExtractor",
    "AudioTranscriber",
    "VideoAnalyzer",
    "WatchPlugin",
]
