from __future__ import annotations

import base64
import hashlib
import os
import tempfile
import threading
import warnings
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .models import MediaAssetRef, MediaAvailability, MediaKind

MAX_MEDIA_BYTES = 20_000_000
MAX_DECODED_PIXELS = 40_000_000
THUMBNAIL_SIZE = (512, 512)
_IMAGE_DECODE_LOCK = threading.Lock()

_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class MediaError(ValueError):
    pass


@contextmanager
def _bounded_image_decode():
    # Pillow's decoded-pixel limit is process-global, so serialize the brief period
    # where SignalDesk applies its stricter local limit.
    with _IMAGE_DECODE_LOCK:
        previous_limit = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = MAX_DECODED_PIXELS
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                yield
        finally:
            Image.MAX_IMAGE_PIXELS = previous_limit


def _detected_mime(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


class MediaStore:
    """Content-addressed local media storage with a deliberately small safe format set."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.thumbnail_root = self.root / "thumbnails"
        self.thumbnail_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _dimensions(content: bytes) -> tuple[int, int]:
        try:
            with _bounded_image_decode():
                with Image.open(BytesIO(content)) as image:
                    width, height = image.size
                    image.verify()
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise MediaError("image exceeds the decoded pixel limit") from error
        except (OSError, UnidentifiedImageError) as error:
            raise MediaError("image decoder rejected the file") from error
        if width <= 0 or height <= 0 or width * height > MAX_DECODED_PIXELS:
            raise MediaError("image exceeds the decoded pixel limit")
        return width, height

    def import_bytes(
        self,
        content: bytes,
        *,
        declared_mime: str,
        kind: MediaKind | str = MediaKind.IMAGE,
        original_name: str | None = None,
    ) -> MediaAssetRef:
        if not content:
            raise MediaError("media is empty")
        if len(content) > MAX_MEDIA_BYTES:
            raise MediaError("media exceeds 20 MB")
        detected = _detected_mime(content)
        if detected is None or detected not in _EXTENSIONS:
            raise MediaError("unsupported or unsafe image format")
        if declared_mime.casefold() != detected:
            raise MediaError("declared media type does not match file signature")
        width, height = self._dimensions(content)

        digest = hashlib.sha256(content).hexdigest()
        asset_id = f"media_{digest[:40]}"
        destination = self.root / f"{asset_id}{_EXTENSIONS[detected]}"
        if not destination.exists():
            descriptor, temp_name = tempfile.mkstemp(prefix=".incoming-", dir=self.root)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, destination)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        return MediaAssetRef(
            asset_id=asset_id,
            kind=kind,
            mime_type=detected,
            original_name=(
                original_name.replace("\\", "/").rsplit("/", 1)[-1][:240]
                if original_name
                else None
            ),
            byte_size=len(content),
            width=width,
            height=height,
            availability=MediaAvailability.AVAILABLE,
            sha256=digest,
        )

    def path_for(self, media: MediaAssetRef) -> Path:
        if media.availability != MediaAvailability.AVAILABLE or not media.mime_type:
            raise MediaError("media content is not available")
        extension = _EXTENSIONS.get(media.mime_type)
        if not extension:
            raise MediaError("unsupported media type")
        path = self.root / f"{media.asset_id}{extension}"
        try:
            path.resolve().relative_to(self.root.resolve())
        except ValueError as error:
            raise MediaError("invalid media path") from error
        if not path.is_file():
            raise MediaError("media file is missing")
        return path

    def as_data_url(self, media: MediaAssetRef, *, max_bytes: int = 8_000_000) -> str:
        path = self.path_for(media)
        content = path.read_bytes()
        if len(content) > max_bytes:
            raise MediaError("media is too large for model input")
        encoded = base64.b64encode(content).decode("ascii")
        return f"data:{media.mime_type};base64,{encoded}"

    def thumbnail_path_for(self, media: MediaAssetRef) -> Path:
        source = self.path_for(media)
        destination = self.thumbnail_root / f"{media.asset_id}.png"
        if destination.is_file():
            return destination
        descriptor, temp_name = tempfile.mkstemp(prefix=".thumb-", dir=self.thumbnail_root)
        os.close(descriptor)
        try:
            with _bounded_image_decode():
                with Image.open(source) as image:
                    image.seek(0)
                    normalized = ImageOps.exif_transpose(image)
                    normalized.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                    if normalized.mode not in {"RGB", "RGBA"}:
                        normalized = normalized.convert("RGBA")
                    normalized.save(temp_name, format="PNG", optimize=True)
            os.replace(temp_name, destination)
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise MediaError("image exceeds the decoded pixel limit") from error
        except (OSError, UnidentifiedImageError) as error:
            raise MediaError("thumbnail generation failed") from error
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return destination

    def delete(self, media: MediaAssetRef) -> bool:
        try:
            path = self.path_for(media)
        except MediaError:
            return False
        path.unlink()
        thumbnail = self.thumbnail_root / f"{media.asset_id}.png"
        if thumbnail.exists():
            thumbnail.unlink()
        return True

    def clear(self) -> int:
        removed = 0
        for path in self.root.iterdir():
            managed = path.name.startswith(("media_", ".incoming-"))
            if path.is_file() and managed:
                path.unlink()
                removed += 1
        for path in self.thumbnail_root.iterdir():
            if path.is_file():
                path.unlink()
                removed += 1
        return removed
