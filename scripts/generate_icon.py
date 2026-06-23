import argparse
from pathlib import Path

from PIL import Image, ImageDraw


DEFAULT_OUTPUT = Path("assets/hyperv-dashboard.ico")
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def create_icon_image(size: int) -> Image.Image:
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


def generate_icon(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images = [create_icon_image(size) for size in ICON_SIZES]
    images[-1].save(output_path, sizes=[(size, size) for size in ICON_SIZES])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Hyper-V Dashboard icon")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Icon output path. Defaults to {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_icon(args.output)
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()
