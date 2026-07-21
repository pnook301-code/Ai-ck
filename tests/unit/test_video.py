"""Tests for Video Analysis System"""

import os
import tempfile

import cv2
import numpy as np
import pytest

from kernel.video import (
    VideoSourceType, FrameInfo, TranscriptSegment, Transcript,
    VideoMeta, VideoAnalysisResult, SceneDetector,
    VideoFrameExtractor, AudioTranscriber, VideoAnalyzer, WatchPlugin,
)


@pytest.fixture(scope="session")
def test_video():
    path = os.path.join(tempfile.mkdtemp(), "test_video.mp4")
    fps = 10
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (320, 240))
    colors = [(255,255,255),(0,0,0),(255,0,0),(0,255,0),(0,0,255)]
    for i in range(50):
        c = colors[i // 10 % len(colors)]
        frame = np.full((240, 320, 3), c, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestSceneDetector:
    def test_detect_empty(self):
        assert SceneDetector().detect([]) == []

    def test_detect_no_change(self):
        sd = SceneDetector(threshold=0.5)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frames = [(i, frame.copy(), i / 10.0) for i in range(20)]
        selected = sd.detect(frames)
        assert len(selected) >= 1

    def test_detect_scene_changes(self, test_video):
        sd = SceneDetector(threshold=0.3)
        cap = cv2.VideoCapture(test_video)
        frames_buf, idx = [], 0
        while True:
            ret, frame = cap.read()
            if not ret: break
            frames_buf.append((idx, frame, idx / 10.0))
            idx += 1
        cap.release()
        assert len(sd.detect(frames_buf)) >= 3

    def test_max_frames(self):
        sd = SceneDetector(max_frames=3)
        frames = [(i, np.full((10,10,3), (i*50)%256, dtype=np.uint8), i/10.0) for i in range(50)]
        assert len(sd.detect(frames)) <= 3

    def test_detect_from_path(self, test_video):
        results = SceneDetector(threshold=0.3).detect_from_path(test_video, fps_sample=5)
        assert len(results) > 0
        for idx, ts, score in results:
            assert isinstance(idx, int)
            assert isinstance(ts, float)


class TestTranscript:
    def test_segment(self):
        seg = TranscriptSegment(start=1.0, end=2.5, text="hello", confidence=0.95)
        assert seg.text == "hello"

    def test_text_around(self):
        t = Transcript(segments=[
            TranscriptSegment(0, 1, "intro"),
            TranscriptSegment(5, 6, "middle"),
            TranscriptSegment(10, 11, "outro"),
        ])
        assert "middle" in t.text_around(5.0, window=3.0)
        assert t.text_around(0, window=1) != ""

    def test_full_text(self):
        t = Transcript(full_text="hello", duration_sec=10.0)
        assert t.duration_sec == 10.0


class TestFrameInfo:
    def test_basic(self):
        fi = FrameInfo(index=42, timestamp_sec=10.5, timestamp_str="00:00:10", path="/tmp/frame.jpg")
        assert fi.index == 42


class TestVideoMeta:
    def test_defaults(self):
        assert VideoMeta().source_type == VideoSourceType.URL


class TestVideoAnalysisResult:
    def test_defaults(self):
        r = VideoAnalysisResult()
        assert r.id.startswith("va_")
        assert r.error is None

    def test_summary(self):
        r = VideoAnalysisResult(
            query="test", keyframes_extracted=10, total_frames_in_video=500,
            transcript=Transcript(segments=[TranscriptSegment(0,1,"hi")]),
            meta=VideoMeta(duration_sec=30.0), processing_time_sec=5.5,
        )
        s = r.summary
        assert s["frames"] == 10
        assert s["transcript_segments"] == 1

    def test_summary_error(self):
        s = VideoAnalysisResult(error="broke").summary
        assert s["error"] == "broke"


class TestVideoFrameExtractor:
    def test_extract_local(self, test_video):
        fe = VideoFrameExtractor()
        try:
            frames, meta, _ = fe.extract(test_video, VideoSourceType.LOCAL)
            assert len(frames) >= 1
            assert meta.width == 320
            for f in frames:
                assert os.path.exists(f.path)
        finally:
            fe.cleanup()

    def test_probe(self, test_video):
        meta = VideoFrameExtractor()._probe(test_video)
        assert meta.width == 320 and meta.fps > 0

    def test_cleanup(self):
        fe = VideoFrameExtractor()
        d = fe._work_dir
        assert os.path.exists(d)
        fe.cleanup()
        assert not os.path.exists(d)

    def test_nonexistent(self):
        with pytest.raises(FileNotFoundError):
            VideoFrameExtractor().extract("/bad.mp4", VideoSourceType.LOCAL)


class TestAudioTranscriber:
    def test_find_ffmpeg(self):
        p = AudioTranscriber()._ffmpeg_path
        assert p and os.path.exists(p)

    def test_extract_audio_silence_fallback(self, test_video):
        at = AudioTranscriber()
        audio = at._extract_audio(test_video)
        assert os.path.exists(audio) and os.path.getsize(audio) > 0

    def test_generate_silence(self, tmp_path):
        out = str(tmp_path / "silence.wav")
        AudioTranscriber()._generate_silence(out, 2.0)
        assert os.path.exists(out) and os.path.getsize(out) > 0


class TestWatchPlugin:
    def test_name(self):
        assert WatchPlugin().name == "watch"

    def test_parse_full(self):
        r = WatchPlugin().parse("/watch https://youtube.com/watch?v=abc What?")
        assert r["source_type"] == VideoSourceType.YOUTUBE
        assert r["query"] == "What?"

    def test_parse_no_query(self):
        r = WatchPlugin().parse("/watch https://example.com/v.mp4")
        assert r["query"] == "Summarize this video"

    def test_parse_not_watch(self):
        assert WatchPlugin().parse("hello") is None
        assert WatchPlugin().parse("") is None

    def test_parse_local(self):
        r = WatchPlugin().parse("/watch /tmp/v.mp4 Describe")
        assert r["source_type"] == VideoSourceType.LOCAL

    def test_parse_tiktok(self):
        r = WatchPlugin().parse("/watch https://tiktok.com/@u/v/123")
        assert r["source_type"] == VideoSourceType.TIKTOK

    def test_parse_instagram(self):
        r = WatchPlugin().parse("/watch https://instagram.com/p/ABC/")
        assert r["source_type"] == VideoSourceType.INSTAGRAM

    def test_commands(self):
        assert WatchPlugin().commands[0]["name"] == "watch"

    def test_description(self):
        assert "video" in WatchPlugin().description.lower()

    def test_detect_source_type_custom(self):
        wp = WatchPlugin()
        assert wp._detect_source_type("/local/file.mp4") == VideoSourceType.LOCAL
        assert wp._detect_source_type("https://other.com/v") == VideoSourceType.URL


class TestVideoAnalyzer:
    def test_analyze_no_llm(self, test_video):
        class MockTranscriber:
            def transcribe(self, path, language=None, time_start=None, time_end=None):
                return Transcript(
                    segments=[TranscriptSegment(0.0, 1.0, "mock transcript text", 0.9)],
                    full_text="mock transcript text", language="en", duration_sec=5.0,
                )
        fe = VideoFrameExtractor()
        va = VideoAnalyzer(frame_extractor=fe, transcriber=MockTranscriber())
        r = va.analyze(test_video, source_type=VideoSourceType.LOCAL)
        assert r.meta is not None
        assert r.frames is not None
        assert r.transcript is not None
        assert r.transcript.segments[0].text == "mock transcript text"

    def test_analyze_with_mock_llm(self, test_video):
        class MockTranscriber:
            def transcribe(self, path, language=None, time_start=None, time_end=None):
                return Transcript(
                    segments=[TranscriptSegment(0.0, 2.0, "hello world", 0.8)],
                    full_text="hello world", language="en", duration_sec=5.0,
                )
        def mock_llm(prompt, frames=None):
            return f"saw {len(frames)} frames and analyzed"
        fe = VideoFrameExtractor()
        va = VideoAnalyzer(frame_extractor=fe, transcriber=MockTranscriber(), llm_callback=mock_llm)
        r = va.analyze(test_video, query="describe", source_type=VideoSourceType.LOCAL)
        assert "frames and analyzed" in r.answer

    def test_analyze_with_error(self, test_video):
        class FailTranscriber:
            def transcribe(self, path, **kw):
                raise RuntimeError("whisper crash")
        fe = VideoFrameExtractor()
        va = VideoAnalyzer(frame_extractor=fe, transcriber=FailTranscriber())
        r = va.analyze(test_video, source_type=VideoSourceType.LOCAL)
        assert r.error is not None
