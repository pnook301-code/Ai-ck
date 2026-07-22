"""Video frame extractor — downloads video and extracts keyframes at scene changes"""

import os
import tempfile
from typing import List, Optional, Tuple

from .types import FrameInfo, VideoMeta, VideoSourceType
from .scene_detector import SceneDetector


class VideoFrameExtractor:
    def __init__(self, work_dir: str = "", scene_detector: Optional[SceneDetector] = None):
        self._work_dir = work_dir or tempfile.mkdtemp(prefix="ck_video_")
        self._detector = scene_detector or SceneDetector()

    def extract(self, source: str, source_type: VideoSourceType = VideoSourceType.URL,
                time_start: Optional[float] = None, time_end: Optional[float] = None,
                max_frames: int = 200) -> tuple[List[FrameInfo], VideoMeta, str]:
        video_path, meta = self._acquire_video(source, source_type, time_start, time_end)
        frames = self._extract_frames(video_path, meta, max_frames)
        return frames, meta, video_path

    def _validate_source(self, source: str) -> bool:
        from urllib.parse import urlparse
        parsed = urlparse(source)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    def _acquire_video(self, source: str, source_type: VideoSourceType,
                       time_start: Optional[float] = None,
                       time_end: Optional[float] = None) -> tuple[str, VideoMeta]:
        if source_type == VideoSourceType.URL and not self._validate_source(source):
            source_type = VideoSourceType.LOCAL

        if source_type == VideoSourceType.LOCAL:
            if not os.path.exists(source):
                raise FileNotFoundError(f"Video not found: {source}")
            meta = self._probe(source)
            return source, meta

        import yt_dlp
        outtmpl = os.path.join(self._work_dir, "%(id)s.%(ext)s")
        ydl_opts = {
            "outtmpl": outtmpl,
            "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }
        if time_start or time_end:
            ydl_opts["download_ranges"] = lambda info, ctx: [{
                "start_time": time_start or 0,
                "end_time": time_end or info.get("duration", 0),
            }]
            ydl_opts["force_key_frames_at_cuts"] = True

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(source, download=True)
            video_path = ydl.prepare_filename(info)
            if not os.path.exists(video_path):
                base = os.path.splitext(video_path)[0]
                for ext in [".mp4", ".mkv", ".webm"]:
                    candidate = base + ext
                    if os.path.exists(candidate):
                        video_path = candidate
                        break

            meta = VideoMeta(
                title=info.get("title", ""),
                duration_sec=info.get("duration", 0) or 0,
                source_url=source,
                source_type=source_type,
                format=info.get("ext", "mp4"),
            )
        return video_path, meta

    def _extract_frames(self, video_path: str, meta: VideoMeta,
                        max_frames: int = 200) -> List[FrameInfo]:
        import cv2
        import numpy as np
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        meta.fps = video_fps
        meta.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        meta.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        sample_interval = max(1, int(video_fps / 2.0))
        batch: List[Tuple[int, np.ndarray, float]] = []
        selected: List[Tuple[int, np.ndarray, float, float]] = []
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_interval == 0:
                ts = frame_idx / video_fps if video_fps > 0 else 0
                batch.append((frame_idx, frame, ts))
                if len(batch) >= 50:
                    self._detector.max_frames = max_frames
                    selected.extend(self._detector.detect(batch))
                    batch.clear()
                    if len(selected) >= max_frames:
                        break
            frame_idx += 1
        cap.release()

        if batch:
            self._detector.max_frames = max_frames
            selected.extend(self._detector.detect(batch))
            batch.clear()

        self._detector.max_frames = max_frames
        selected = selected[:max_frames]

        frames_dir = os.path.join(self._work_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        result = []
        for idx, frame, ts, score in selected:
            fname = f"frame_{idx:06d}_{ts:.2f}s.jpg"
            fpath = os.path.join(frames_dir, fname)
            cv2.imwrite(fpath, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            h, w = frame.shape[:2]
            result.append(FrameInfo(
                index=idx, timestamp_sec=ts,
                timestamp_str=self._fmt_ts(ts),
                path=fpath, width=w, height=h,
                scene_score=score,
            ))
        return result

    def _probe(self, path: str) -> VideoMeta:
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return VideoMeta(source_type=VideoSourceType.LOCAL)
        meta = VideoMeta(
            source_type=VideoSourceType.LOCAL,
            duration_sec=cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1),
            fps=cap.get(cv2.CAP_PROP_FPS),
            width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            title=os.path.basename(path),
            source_url=path,
        )
        cap.release()
        return meta

    def _fmt_ts(self, sec: float) -> str:
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def cleanup(self):
        import shutil
        if os.path.exists(self._work_dir) and "ck_video_" in self._work_dir:
            shutil.rmtree(self._work_dir, ignore_errors=True)
