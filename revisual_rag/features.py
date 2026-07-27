from __future__ import annotations

import colorsys
import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageFilter, ImageStat

from .unity_meta import SpriteRect


SEMANTIC_DIMENSIONS = 128


@dataclass(frozen=True)
class ImageFeatures:
    width: int
    height: int
    aspect_ratio: float
    alpha_coverage: float
    opaque_bounds_ratio: float
    brightness: float
    saturation: float
    edge_density: float
    dominant_palette: list[str]
    perceptual_hash: str
    visual_vector: list[float]


def _normalize(values: Iterable[float]) -> list[float]:
    vector = list(values)
    length = math.sqrt(sum(value * value for value in vector))
    return [value / length for value in vector] if length else vector


def _pixels(image: Image.Image):
    getter = getattr(image, "get_flattened_data", None)
    return getter() if getter else image.getdata()


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def tokenize(*parts: str | None) -> list[str]:
    words: list[str] = []
    for part in parts:
        if not part:
            continue
        expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", part)
        words.extend(re.findall(r"[a-z0-9]+", expanded.casefold()))
    return words


def semantic_vector(*parts: str | None) -> list[float]:
    vector = [0.0] * SEMANTIC_DIMENSIONS
    words = tokenize(*parts)
    for word in words:
        digest = hashlib.blake2b(word.encode("utf-8"), digest_size=8).digest()
        slot = int.from_bytes(digest[:4], "little") % SEMANTIC_DIMENSIONS
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[slot] += sign
    return _normalize(vector)


def _open_region(path: Path, rect: SpriteRect | None) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    if rect is None:
        return image
    top = image.height - rect.y - rect.height
    return image.crop((rect.x, top, rect.x + rect.width, top + rect.height))


def extract_image_features(path: Path, rect: SpriteRect | None = None) -> ImageFeatures:
    image = _open_region(path, rect)
    width, height = image.size
    sample = image.copy()
    sample.thumbnail((64, 64), Image.Resampling.LANCZOS)

    alpha = sample.getchannel("A")
    alpha_values = list(_pixels(alpha))
    alpha_coverage = sum(1 for value in alpha_values if value > 8) / max(1, len(alpha_values))
    bounds = alpha.getbbox()
    opaque_bounds_ratio = 0.0
    if bounds:
        opaque_bounds_ratio = ((bounds[2] - bounds[0]) * (bounds[3] - bounds[1])) / max(
            1, sample.width * sample.height
        )

    rgb = sample.convert("RGB")
    rgb_stat = ImageStat.Stat(rgb)
    mean_rgb = [value / 255.0 for value in rgb_stat.mean]
    hsv = colorsys.rgb_to_hsv(*mean_rgb)

    quantized = rgb.quantize(colors=5, method=Image.Quantize.MEDIANCUT).convert("RGB")
    counts = Counter(_pixels(quantized))
    palette = [
        "#{:02x}{:02x}{:02x}".format(*color)
        for color, _ in counts.most_common(5)
    ]

    grayscale = rgb.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(_pixels(grayscale))
    hash_bits = []
    for row in range(8):
        offset = row * 9
        hash_bits.extend(pixels[offset + column] > pixels[offset + column + 1] for column in range(8))
    phash = f"{sum((1 << index) for index, bit in enumerate(hash_bits) if bit):016x}"

    edges = rgb.convert("L").filter(ImageFilter.FIND_EDGES)
    edge_density = sum(_pixels(edges)) / max(1, edges.width * edges.height * 255)

    hue_hist = [0.0] * 12
    saturation_sum = 0.0
    brightness_sum = 0.0
    visible = 0
    rgba_pixels = list(_pixels(sample))
    for red, green, blue, alpha_value in rgba_pixels:
        if alpha_value <= 8:
            continue
        hue, sat, val = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
        hue_hist[min(11, int(hue * 12))] += 1.0
        saturation_sum += sat
        brightness_sum += val
        visible += 1
    if visible:
        hue_hist = [value / visible for value in hue_hist]
    brightness = brightness_sum / visible if visible else 0.0
    saturation = saturation_sum / visible if visible else 0.0

    visual = _normalize(
        [
            math.log2(max(1, width)) / 16.0,
            math.log2(max(1, height)) / 16.0,
            min(4.0, width / max(1, height)) / 4.0,
            alpha_coverage,
            opaque_bounds_ratio,
            brightness,
            saturation,
            edge_density,
            *mean_rgb,
            *hue_hist,
        ]
    )
    return ImageFeatures(
        width=width,
        height=height,
        aspect_ratio=round(width / max(1, height), 6),
        alpha_coverage=round(alpha_coverage, 6),
        opaque_bounds_ratio=round(opaque_bounds_ratio, 6),
        brightness=round(brightness, 6),
        saturation=round(saturation, 6),
        edge_density=round(edge_density, 6),
        dominant_palette=palette,
        perceptual_hash=phash,
        visual_vector=visual,
    )
