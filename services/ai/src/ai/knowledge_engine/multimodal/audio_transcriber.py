"""Audio Transcriber — transcribes audio files using faster-whisper.

Uses faster-whisper (CTranslate2 implementation of Whisper) for local,
free speech-to-text. No API keys needed. Supports:
- Meeting recordings
- Podcasts
- Voice notes
- Multi-language audio
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass, field
import contextlib

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result from audio transcription."""
    text: str
    language: str | None = None
    language_probability: float = 0.0
    duration_seconds: float = 0.0
    segments: list[dict] = field(default_factory=list)
    total_characters: int = 0
    metadata: dict = field(default_factory=dict)


class AudioTranscriber:
    """Transcribes audio using faster-whisper."""

    # Model sizes: tiny, base, small, medium, large-v2, large-v3
    # larger = more accurate but slower
    DEFAULT_MODEL = "base"

    def __init__(self, model_size: str | None = None):
        self.model_size = model_size or self.DEFAULT_MODEL
        self._model = None

    def _get_model(self):
        """Lazy-load the Whisper model."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                )
            except ImportError:
                raise RuntimeError(
                    "faster-whisper is not installed. "
                    "Install with: pip install faster-whisper"
                ) from None
        return self._model

    async def transcribe_from_bytes(
        self,
        audio_bytes: bytes,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe raw audio bytes."""
        # Write to temp file since faster-whisper needs a file path
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            return await self._transcribe_file(tmp_path, language)
        finally:
            import os
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)

    async def transcribe_from_path(
        self,
        file_path: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe an audio file path."""
        return await self._transcribe_file(file_path, language)

    async def _transcribe_file(
        self,
        file_path: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe an audio file."""
        model = self._get_model()

        try:
            segments_raw, info = model.transcribe(
                file_path,
                language=language,
                beam_size=5,
                vad_filter=True,  # Voice Activity Detection for better quality
                vad_parameters={
                    "min_silence_duration_ms": 500,
                },
            )

            # Collect segments
            segments = []
            full_text_parts = []

            for segment in segments_raw:
                segment_dict = {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                }
                segments.append(segment_dict)
                full_text_parts.append(segment.text.strip())

            full_text = " ".join(full_text_parts)

            result = TranscriptionResult(
                text=full_text,
                language=info.language,
                language_probability=round(info.language_probability, 3),
                duration_seconds=round(info.duration, 2),
                segments=segments,
                total_characters=len(full_text),
                metadata={
                    "model_size": self.model_size,
                    "segment_count": len(segments),
                },
            )

            logger.info(
                "Audio transcribed: %.1fs, %d segments, lang=%s (%.1f%%)",
                result.duration_seconds,
                len(segments),
                result.language,
                result.language_probability * 100,
            )
            return result

        except Exception as e:
            logger.warning("Transcription failed: %s", e)
            return TranscriptionResult(
                text="",
                metadata={"error": str(e)},
            )

    async def transcribe_from_url(self, url: str) -> TranscriptionResult:
        """Download audio from URL and transcribe."""
        import httpx

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        return await self.transcribe_from_bytes(resp.content)

    def get_supported_formats(self) -> list[str]:
        """Return supported file extensions."""
        return [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".mp4"]
