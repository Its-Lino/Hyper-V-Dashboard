import io
from pathlib import Path

from fastapi.responses import FileResponse, Response
from PIL import Image, ImageDraw

from .constants import ICON_FILE
from .paths import resource_path


def create_app_icon_image(size: int = 256) -> Image.Image:
    scale = size / 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(left: int, top: int, right: int, bottom: int) -> tuple[int, int, int, int]:
        return (
            round(left * scale),
            round(top * scale),
            round(right * scale),
            round(bottom * scale),
        )

    def radius(value: int) -> int:
        return max(1, round(value * scale))

    draw.rounded_rectangle(box(0, 0, 256, 256), radius=radius(56), fill="#1E293B")
    draw.rounded_rectangle(box(48, 56, 208, 168), radius=radius(16), fill="#2563EB")
    draw.rounded_rectangle(box(66, 76, 190, 150), radius=radius(8), fill="#0F172A")
    draw.rounded_rectangle(box(86, 94, 170, 106), radius=radius(6), fill="#38BDF8")
    draw.rounded_rectangle(box(86, 118, 134, 130), radius=radius(6), fill="#22C55E")
    draw.polygon(
        [
            (round(104 * scale), round(184 * scale)),
            (round(152 * scale), round(184 * scale)),
            (round(160 * scale), round(208 * scale)),
            (round(96 * scale), round(208 * scale)),
        ],
        fill="#60A5FA",
    )
    draw.rounded_rectangle(box(72, 208, 184, 224), radius=radius(8), fill="#93C5FD")
    return image


def generated_icon_path() -> Path:
    return Path(resource_path(str(ICON_FILE)))


def favicon_response() -> Response:
    icon_path = generated_icon_path()
    if icon_path.exists():
        return FileResponse(icon_path, media_type="image/x-icon")

    buffer = io.BytesIO()
    create_app_icon_image().save(
        buffer,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )
    return Response(content=buffer.getvalue(), media_type="image/x-icon")
