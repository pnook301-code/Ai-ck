"""Scene change detector — identifies keyframes where visual content changes"""

from typing import List, Optional, Tuple
import numpy as np


class SceneDetector:
    _cv2 = None

    @classmethod
    def _cv(cls):
        if cls._cv2 is None:
            import cv2
            cls._cv2 = cv2
        return cls._cv2
    MIN_SCENE_CHANGE = 0.3
    MAX_FRAMES = 200
    MIN_FRAME_INTERVAL = 0.5

    def __init__(self, threshold: float = MIN_SCENE_CHANGE,
                 max_frames: int = MAX_FRAMES,
                 min_interval_sec: float = MIN_FRAME_INTERVAL):
        self.threshold = threshold
        self.max_frames = max_frames
        self.min_interval_sec = min_interval_sec

    def detect(self, frames: List[Tuple[int, np.ndarray, float]]) -> List[Tuple[int, np.ndarray, float, float]]:
        if not frames:
            return []

        selected = []
        last_selected_time = -self.min_interval_sec
        prev_hist = None

        for idx, frame, timestamp in frames:
            if len(selected) >= self.max_frames:
                break
            score = 0.0
            if prev_hist is not None:
                hist = self._histogram(frame)
                score = self._hist_diff(prev_hist, hist)
                if score < self.threshold and (timestamp - last_selected_time) < self.min_interval_sec:
                    continue
                if score < self.threshold:
                    continue
                if (timestamp - last_selected_time) < self.min_interval_sec:
                    continue
                prev_hist = hist
            else:
                prev_hist = self._histogram(frame)

            selected.append((idx, frame, timestamp, score))
            last_selected_time = timestamp

        if len(selected) < 2 and len(frames) > 1:
            mid = len(frames) // 2
            idx, frame, ts = frames[mid]
            if not any(s[0] == idx for s in selected):
                selected.append((idx, frame, ts, 0.0))

        return selected

    def detect_from_path(self, video_path: str, fps_sample: float = 1.0) -> List[Tuple[int, float, float]]:
        cv2 = self._cv()
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_interval = max(1, int(video_fps / fps_sample))
        frames_buf: List[Tuple[int, np.ndarray, float]] = []
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_interval == 0:
                ts = frame_idx / video_fps if video_fps > 0 else 0
                frames_buf.append((frame_idx, frame, ts))
            frame_idx += 1
        cap.release()

        results = self.detect(frames_buf)
        return [(r[0], r[2], r[3]) for r in results]

    def _histogram(self, frame: np.ndarray) -> np.ndarray:
        cv2 = self._cv()
        small = cv2.resize(frame, (64, 48))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [8, 8], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        return hist.flatten()

    def _hist_diff(self, h1: np.ndarray, h2: np.ndarray) -> float:
        cv2 = self._cv()
        return float(cv2.compareHist(h1, h2, cv2.HISTCMP_CHISQR))
