"""Extracao de frames de video para analise por IA."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path

import cv2


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractedFrame:
    index: int
    timestamp_s: float
    timestamp_formatado: str
    path: str
    width: int
    height: int


def _format_timestamp(seconds: float) -> str:
    total_centiseconds = int(round(seconds * 100))
    minutes = total_centiseconds // 6000
    remaining_centiseconds = total_centiseconds % 6000
    second_value = remaining_centiseconds / 100
    return f"{minutes:02d}:{second_value:05.2f}"


def _format_timestamp_for_filename(seconds: float) -> str:
    return f"{seconds:06.2f}s"


def _frame_timestamp(frame_number: int, source_fps: float, capture_msec: float) -> float:
    if source_fps > 0:
        return frame_number / source_fps
    if capture_msec > 0:
        return capture_msec / 1000
    return 0.0


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _resize_to_max_width(frame, max_width: int):
    if max_width <= 0:
        return frame
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame
    scale = max_width / width
    return cv2.resize(frame, (max_width, int(height * scale)), interpolation=cv2.INTER_AREA)


def _write_jpeg(frame_path: Path, frame, jpeg_quality: int) -> None:
    quality = max(1, min(100, int(jpeg_quality)))
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError(f"Nao foi possivel salvar frame em: {frame_path}")
    encoded.tofile(str(frame_path))


def extract_frames(
    video_path: str,
    output_dir: str,
    fps: float = 1.0,
    max_frames: int | None = None,
) -> list[ExtractedFrame]:
    """Extrai frames JPEG de um video em uma taxa amostral definida."""

    if fps <= 0:
        raise ValueError("fps deve ser maior que zero")
    if max_frames is not None and max_frames < 0:
        raise ValueError("max_frames deve ser maior ou igual a zero")

    source_path = Path(video_path)
    destination = Path(output_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Video nao encontrado: {source_path}")
    if source_path.stat().st_size <= 0:
        raise ValueError(f"Video vazio ou invalido: {source_path}")

    logger.info("Video recebido para extracao: %s", source_path)
    logger.info("Tamanho do video: %s bytes", source_path.stat().st_size)
    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        raise ValueError(f"Não foi possível abrir o vídeo: {source_path}")

    destination.mkdir(parents=True, exist_ok=True)

    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_s = frame_count / source_fps if source_fps > 0 and frame_count > 0 else 0.0
    logger.info(
        "Video aberto: fps_original=%.3f frames=%s duracao_aproximada_s=%.3f",
        source_fps,
        frame_count,
        duration_s,
    )
    sampling_interval_s = 1.0 / fps
    next_timestamp_s = 0.0
    extracted: list[ExtractedFrame] = []
    frame_number = 0

    try:
        while True:
            if max_frames is not None and len(extracted) >= max_frames:
                break

            ok, frame = capture.read()
            if not ok:
                break

            capture_msec = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
            timestamp_s = _frame_timestamp(frame_number, source_fps, capture_msec)

            if timestamp_s + 1e-9 >= next_timestamp_s:
                frame_index = len(extracted) + 1
                height, width = frame.shape[:2]
                filename = f"frame_{frame_index:06d}_{_format_timestamp_for_filename(timestamp_s)}.jpg"
                frame_path = destination / filename

                _write_jpeg(frame_path, frame, jpeg_quality=95)

                extracted.append(
                    ExtractedFrame(
                        index=frame_index,
                        timestamp_s=round(timestamp_s, 3),
                        timestamp_formatado=_format_timestamp(timestamp_s),
                        path=str(frame_path),
                        width=int(width),
                        height=int(height),
                    )
                )
                next_timestamp_s += sampling_interval_s

            frame_number += 1
    finally:
        capture.release()

    if not extracted:
        raise ValueError(f"Nenhum frame foi extraido do video: {source_path}")

    logger.info(
        "Frames extraidos: %s de %s para %s",
        len(extracted),
        source_path,
        destination,
    )
    return sorted(extracted, key=lambda item: item.timestamp_s)


def extract_representative_frames(
    video_path: str,
    output_dir: str,
    sample_interval_s: float = 1.0,
) -> list[ExtractedFrame]:
    """Extract JPEG frames across the full video while preserving real timestamps."""

    if sample_interval_s <= 0:
        raise ValueError("sample_interval_s deve ser maior que zero")

    source_path = Path(video_path)
    destination = Path(output_dir)
    if not source_path.exists():
        raise FileNotFoundError(f"Video nao encontrado: {source_path}")
    if source_path.stat().st_size <= 0:
        raise ValueError(f"Video vazio ou invalido: {source_path}")

    max_width = _read_int_env("OPENAI_FRAME_MAX_WIDTH", 1024)
    jpeg_quality = _read_int_env("OPENAI_JPEG_QUALITY", 75)

    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        raise ValueError(f"Nao foi possivel abrir o video: {source_path}")

    destination.mkdir(parents=True, exist_ok=True)
    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_s = frame_count / source_fps if source_fps > 0 and frame_count > 0 else 0.0

    extracted: list[ExtractedFrame] = []
    frame_number = 0
    next_timestamp_s = 0.0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            capture_msec = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
            timestamp_s = _frame_timestamp(frame_number, source_fps, capture_msec)
            is_last_frame = (
                duration_s > 0
                and frame_count > 0
                and frame_number >= max(frame_count - 1, 0)
            )

            if timestamp_s + 1e-9 >= next_timestamp_s or is_last_frame:
                frame = _resize_to_max_width(frame, max_width=max_width)
                height, width = frame.shape[:2]
                frame_index = len(extracted) + 1
                filename = f"frame_{frame_index:06d}_{_format_timestamp_for_filename(timestamp_s)}.jpg"
                frame_path = destination / filename
                _write_jpeg(frame_path, frame, jpeg_quality=jpeg_quality)
                extracted.append(
                    ExtractedFrame(
                        index=frame_index,
                        timestamp_s=round(timestamp_s, 3),
                        timestamp_formatado=_format_timestamp(timestamp_s),
                        path=str(frame_path),
                        width=int(width),
                        height=int(height),
                    )
                )
                next_timestamp_s += sample_interval_s

            frame_number += 1
    finally:
        capture.release()

    if not extracted:
        raise ValueError(f"Nenhum frame foi extraido do video: {source_path}")

    return sorted(extracted, key=lambda item: item.timestamp_s)
