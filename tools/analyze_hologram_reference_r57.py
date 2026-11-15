"""Measure the user's decoded videos without treating filming artifacts as source UI.

Run locally after the five references have been decoded under /workspace.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates, maximum_filter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/workspace/Cronos-reference-complete')
OUT = ROOT / 'docs/visual-audit-r57'


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def state(frame: int) -> str:
    if 127 <= frame <= 297:
        return 'FALANDO'
    if 299 <= frame <= 305:
        return 'EM ESPERA'
    if 308 <= frame <= 362:
        return 'OUVINDO'
    return 'TRANSICAO'


def apparent_widths(field: np.ndarray, x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    sampled = map_coordinates(field, [y, x], order=1, mode='nearest') > 45
    widths = []
    for row in sampled:
        edges = np.diff(np.r_[False, row, False].astype(np.int8))
        starts = np.flatnonzero(edges == 1)
        ends = np.flatnonzero(edges == -1)
        widths.extend(width for width in ends - starts if 1 <= width <= 12)
    if not widths:
        return 0.0, 0.0
    return float(np.median(widths)), float(np.quantile(widths, .9))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_frames = []
    for video in range(1, 6):
        name = f'v{video:02d}'
        with (SOURCE / name / 'frames.csv').open(newline='', encoding='utf-8') as stream:
            for row in csv.DictReader(stream):
                row['duration'] = f"{float(row['duration']):.6f}"
                all_frames.append({'video': name, **row})
    assert len(all_frames) == 9920
    write_csv(OUT / 'all-video-frames.csv', all_frames)

    yy, xx = np.indices((510, 510), dtype=np.float32)
    radius = np.hypot(xx - 255, yy - 255)
    annulus = (radius >= 138) & (radius <= 240) & (yy < 470)
    angles = np.linspace(-np.pi, np.pi, 640, endpoint=False)
    radii = np.arange(140, 241, dtype=np.float32)
    px = 255 + np.cos(angles)[:, None] * radii[None, :]
    py = 255 - np.sin(angles)[:, None] * radii[None, :]
    source_times = {int(row['frame']): row for row in all_frames if row['video'] == 'v05'}
    measurements = []
    for frame in range(127, 363):
        image = np.asarray(Image.open(SOURCE / 'v05/stabilized' / f'{frame:05d}.jpg'), dtype=np.float32)
        red, green, blue = image.transpose(2, 0, 1)
        cyan_raw = green - red - .08 * blue
        blue_raw = blue - 1.1 * red
        cyan = np.maximum(cyan_raw - gaussian_filter(cyan_raw, 7) * .78, 0)
        blue_contrast = np.maximum(blue_raw - gaussian_filter(blue_raw, 7) * .83, 0)
        led = annulus & (cyan > 45) & (green > 120) & (blue > 160) & (red < 110)
        dim = annulus & (blue_contrast > 28) & (cyan < 45)
        widths = apparent_widths(cyan, px, py)
        smoothed = gaussian_filter(cyan, 1)
        local_peaks = annulus & (smoothed >= maximum_filter(smoothed, size=9)) & (smoothed > 65) & (green > 150)
        colors = np.median(image[led], axis=0) if led.any() else np.zeros(3)
        pixels = radius[led]
        source = source_times[frame]
        measurements.append({
            'frame': frame,
            'pts': source['pts'],
            'state': state(frame),
            'audio_dbfs': source['audio_dbfs'],
            'led_pixels': int(led.sum()),
            'dim_blue_pixels': int(dim.sum()),
            'led_red_median': round(float(colors[0]), 2),
            'led_green_median': round(float(colors[1]), 2),
            'led_blue_median': round(float(colors[2]), 2),
            'led_width_radial_median_px': widths[0],
            'led_width_radial_p90_px': round(widths[1], 2),
            'led_radius_p98_px': round(float(np.quantile(pixels, .98)), 2) if pixels.size else 0,
            'bright_local_peaks_proxy': int(local_peaks.sum()),
            'frame_difference': source['frame_difference'],
        })
    write_csv(OUT / 'front-orb-every-frame.csv', measurements)
    summary = {'total_video_frames': len(all_frames), 'front_orb_frames': len(measurements), 'states': {}}
    for name in ['FALANDO', 'EM ESPERA', 'OUVINDO']:
        group = [row for row in measurements if row['state'] == name]
        summary['states'][name] = {
            'frames': len(group),
            'median_led_pixels': round(float(np.median([row['led_pixels'] for row in group]))),
            'median_dim_blue_pixels': round(float(np.median([row['dim_blue_pixels'] for row in group]))),
            'median_led_rgb': [round(float(np.median([row[f'led_{channel}_median'] for row in group]))) for channel in ['red', 'green', 'blue']],
            'median_apparent_width_px': round(float(np.median([row['led_width_radial_median_px'] for row in group])), 2),
            'p90_apparent_width_px': round(float(np.median([row['led_width_radial_p90_px'] for row in group])), 2),
            'median_outer_led_radius_px': round(float(np.median([row['led_radius_p98_px'] for row in group])), 2),
            'median_bright_local_peaks_proxy': round(float(np.median([row['bright_local_peaks_proxy'] for row in group]))),
        }
    (OUT / 'front-orb-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
