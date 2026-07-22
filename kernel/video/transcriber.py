"""Audio transcriber — extracts audio from video and transcribes with timestamps"""

import os
import shutil
import subprocess
import tempfile
from typing import List, Optional

from .types import Transcript, TranscriptSegment


class AudioTranscriber:
    def __init__(self, model_size: str = "base", device: str = "cpu",
                 compute_type: str = "int8", ffmpeg_path: str = ""):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._ffmpeg_path = ffmpeg_path or self._find_ffmpeg()
        self._model = None
        self._audio_temp_dirs: List[str] = []

    def transcribe(self, video_path: str,
                   language: Optional[str] = None,
                   time_start: Optional[float] = None,
                   time_end: Optional[float] = None) -> Transcript:
        audio_path = self._extract_audio(video_path, time_start, time_end)
        try:
            return self._transcribe_audio(audio_path, language)
        finally:
            audio_dir = os.path.dirname(audio_path)
            if os.path.exists(audio_dir) and "ck_audio_" in audio_dir:
                shutil.rmtree(audio_dir, ignore_errors=True)

    def _extract_audio(self, video_path: str,
                       time_start: Optional[float] = None,
                       time_end: Optional[float] = None) -> str:
        audio_dir = tempfile.mkdtemp(prefix="ck_audio_")
        self._audio_temp_dirs.append(audio_dir)
        audio_path = os.path.join(audio_dir, "audio.wav")
        cmd = [self._ffmpeg_path, "-y", "-i", video_path]
        if time_start is not None:
            cmd.extend(["-ss", str(time_start)])
        if time_end is not None:
            cmd.extend(["-to", str(time_end)])
        cmd.extend(["-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path])
        subprocess.run(cmd, capture_output=True, timeout=600)
        if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
            duration = (time_end or 30) - (time_start or 0)
            if duration <= 0:
                import cv2
                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                duration = total / max(fps, 1)
            self._generate_silence(audio_path, max(duration, 1))
        return audio_path

    def _generate_silence(self, path: str, duration_sec: float):
        import struct
        import wave
        sample_rate = 16000
        num_samples = int(sample_rate * duration_sec)
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack(f"<{num_samples}h", *([0] * num_samples)))

    def _transcribe_audio(self, audio_path: str,
                          language: Optional[str] = None) -> Transcript:
        from faster_whisper import WhisperModel
        if self._model is None:
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        segments, info = self._model.transcribe(audio_path, language=language)
        result = Transcript(
            language=info.language,
            duration_sec=info.duration,
        )
        full_parts = []
        for seg in segments:
            result.segments.append(TranscriptSegment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                confidence=seg.avg_logprob,
                language=info.language or "",
            ))
            full_parts.append(seg.text.strip())
        result.full_text = " ".join(full_parts)
        return result

    def cleanup(self):
        for d in self._audio_temp_dirs:
            if os.path.exists(d) and "ck_audio_" in d:
                shutil.rmtree(d, ignore_errors=True)
        self._audio_temp_dirs.clear()

    def _find_ffmpeg(self) -> str:
        try:
            import imageio_ffmpeg as iof
            return iof.get_ffmpeg_exe()
        except Exception:
            for candidate in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
                try:
                    subprocess.run([candidate, "-version"], capture_output=True, timeout=5)
                    return candidate
                except Exception:
                    continue
            raise RuntimeError("ffmpeg not found. Install ffmpeg or imageio-ffmpeg")
