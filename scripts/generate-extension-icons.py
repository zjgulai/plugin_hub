from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ICON_ROOT = REPO_ROOT / "apps" / "extension" / "public" / "icons"
SIZES = (16, 32, 48, 128)


Color = tuple[int, int, int, int]


def clamp(value: int) -> int:
    return max(0, min(255, value))


def rgba(hex_color: str, alpha: int = 255) -> Color:
    value = hex_color.lstrip("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
        alpha,
    )


def mix(a: Color, b: Color, amount: float) -> Color:
    return (
        clamp(round(a[0] + (b[0] - a[0]) * amount)),
        clamp(round(a[1] + (b[1] - a[1]) * amount)),
        clamp(round(a[2] + (b[2] - a[2]) * amount)),
        clamp(round(a[3] + (b[3] - a[3]) * amount)),
    )


class Canvas:
    def __init__(self, size: int) -> None:
        self.size = size
        self.pixels: list[list[Color]] = [
            [(0, 0, 0, 0) for _ in range(size)] for _ in range(size)
        ]

    def set(self, x: int, y: int, color: Color) -> None:
        if 0 <= x < self.size and 0 <= y < self.size:
            self.pixels[y][x] = color

    def fill_gradient(self, start: Color, end: Color) -> None:
        for y in range(self.size):
            for x in range(self.size):
                amount = (x + y) / max(1, 2 * (self.size - 1))
                self.set(x, y, mix(start, end, amount))

    def rounded_rect(self, x0: float, y0: float, x1: float, y1: float, radius: float, color: Color) -> None:
        sx0 = round(x0 * self.size)
        sy0 = round(y0 * self.size)
        sx1 = round(x1 * self.size)
        sy1 = round(y1 * self.size)
        sr = radius * self.size
        for y in range(sy0, sy1):
            for x in range(sx0, sx1):
                cx = min(max(x, sx0 + sr), sx1 - sr - 1)
                cy = min(max(y, sy0 + sr), sy1 - sr - 1)
                if (x - cx) ** 2 + (y - cy) ** 2 <= sr**2:
                    self.set(x, y, color)

    def circle(self, cx: float, cy: float, radius: float, color: Color) -> None:
        scx = cx * self.size
        scy = cy * self.size
        sr = radius * self.size
        x0 = math.floor(scx - sr)
        x1 = math.ceil(scx + sr)
        y0 = math.floor(scy - sr)
        y1 = math.ceil(scy + sr)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if (x - scx) ** 2 + (y - scy) ** 2 <= sr**2:
                    self.set(x, y, color)

    def line(self, x0: float, y0: float, x1: float, y1: float, width: float, color: Color) -> None:
        sx0 = x0 * self.size
        sy0 = y0 * self.size
        sx1 = x1 * self.size
        sy1 = y1 * self.size
        sw = max(1.0, width * self.size)
        steps = max(1, round(math.hypot(sx1 - sx0, sy1 - sy0) * 2))
        for step in range(steps + 1):
            t = step / steps
            x = sx0 + (sx1 - sx0) * t
            y = sy0 + (sy1 - sy0) * t
            self.circle(x / self.size, y / self.size, sw / (2 * self.size), color)

    def poly(self, points: list[tuple[float, float]], color: Color) -> None:
        scaled = [(x * self.size, y * self.size) for x, y in points]
        min_x = math.floor(min(x for x, _ in scaled))
        max_x = math.ceil(max(x for x, _ in scaled))
        min_y = math.floor(min(y for _, y in scaled))
        max_y = math.ceil(max(y for _, y in scaled))
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                inside = False
                j = len(scaled) - 1
                for i, (xi, yi) in enumerate(scaled):
                    xj, yj = scaled[j]
                    crosses = (yi > y) != (yj > y)
                    if crosses:
                        x_intersect = (xj - xi) * (y - yi) / ((yj - yi) or 1) + xi
                        if x < x_intersect:
                            inside = not inside
                    j = i
                if inside:
                    self.set(x, y, color)

    def save_png(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        raw_rows = []
        for row in self.pixels:
            raw_rows.append(bytes([0]) + bytes(channel for pixel in row for channel in pixel))
        raw = b"".join(raw_rows)
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", struct.pack(">IIBBBBB", self.size, self.size, 8, 6, 0, 0, 0))
            + png_chunk(b"IDAT", zlib.compress(raw, level=9))
            + png_chunk(b"IEND", b"")
        )


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def draw_amazon(size: int) -> Canvas:
    canvas = Canvas(size)
    canvas.fill_gradient(rgba("#f5b63d"), rgba("#7f5a12"))
    canvas.rounded_rect(0.09, 0.09, 0.91, 0.91, 0.2, rgba("#f8c64d"))
    canvas.rounded_rect(0.25, 0.38, 0.75, 0.77, 0.06, rgba("#fff7df"))
    canvas.rounded_rect(0.29, 0.42, 0.71, 0.73, 0.03, rgba("#fff7df"))
    canvas.line(0.38, 0.39, 0.43, 0.27, 0.045, rgba("#3a2a12"))
    canvas.line(0.43, 0.27, 0.57, 0.27, 0.045, rgba("#3a2a12"))
    canvas.line(0.57, 0.27, 0.62, 0.39, 0.045, rgba("#3a2a12"))
    canvas.line(0.35, 0.61, 0.48, 0.69, 0.038, rgba("#3a2a12"))
    canvas.line(0.48, 0.69, 0.66, 0.59, 0.038, rgba("#3a2a12"))
    canvas.circle(0.70, 0.58, 0.035, rgba("#3a2a12"))
    return canvas


def draw_reddit(size: int) -> Canvas:
    canvas = Canvas(size)
    canvas.fill_gradient(rgba("#ff6f3c"), rgba("#8f2f15"))
    canvas.rounded_rect(0.09, 0.09, 0.91, 0.91, 0.22, rgba("#ff6b35"))
    canvas.rounded_rect(0.22, 0.34, 0.78, 0.73, 0.14, rgba("#fff8f2"))
    canvas.poly([(0.39, 0.71), (0.30, 0.84), (0.53, 0.73)], rgba("#fff8f2"))
    canvas.line(0.55, 0.33, 0.67, 0.20, 0.035, rgba("#fff8f2"))
    canvas.circle(0.70, 0.18, 0.045, rgba("#fff8f2"))
    canvas.circle(0.43, 0.52, 0.045, rgba("#3a1d12"))
    canvas.circle(0.59, 0.52, 0.045, rgba("#3a1d12"))
    canvas.line(0.41, 0.62, 0.50, 0.66, 0.026, rgba("#3a1d12"))
    canvas.line(0.50, 0.66, 0.61, 0.61, 0.026, rgba("#3a1d12"))
    return canvas


def draw_instagram(size: int) -> Canvas:
    canvas = Canvas(size)
    canvas.fill_gradient(rgba("#7b2ff7"), rgba("#ff4f8b"))
    canvas.rounded_rect(0.09, 0.09, 0.91, 0.91, 0.23, rgba("#c13f9d"))
    canvas.rounded_rect(0.24, 0.25, 0.76, 0.76, 0.13, rgba("#fff7fb"))
    canvas.rounded_rect(0.30, 0.31, 0.70, 0.70, 0.09, rgba("#c13f9d"))
    canvas.circle(0.50, 0.51, 0.15, rgba("#fff7fb"))
    canvas.circle(0.50, 0.51, 0.09, rgba("#c13f9d"))
    canvas.circle(0.65, 0.36, 0.045, rgba("#fff7fb"))
    return canvas


DRAWERS = {
    "amazon": draw_amazon,
    "reddit": draw_reddit,
    "instagram": draw_instagram,
}


def main() -> None:
    for target, draw in DRAWERS.items():
        for size in SIZES:
            draw(size).save_png(ICON_ROOT / target / f"icon-{size}.png")


if __name__ == "__main__":
    main()
