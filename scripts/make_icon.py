"""Generate our small geometric waveform icon; no downloaded artwork."""

from pathlib import Path
import struct


def main():
    images = []
    for size in (16, 32, 48, 64, 128):
        points = [
            (0.16, 0.53),
            (0.33, 0.53),
            (0.43, 0.26),
            (0.57, 0.76),
            (0.68, 0.46),
            (0.84, 0.46),
        ]
        pixels = bytearray()
        for y in range(size - 1, -1, -1):
            for x in range(size):
                px, py = (x + 0.5) / size, (y + 0.5) / size
                distance = 1
                for (ax, ay), (bx, by) in zip(points, points[1:]):
                    ratio = max(
                        0,
                        min(
                            1,
                            ((px - ax) * (bx - ax) + (py - ay) * (by - ay))
                            / ((bx - ax) ** 2 + (by - ay) ** 2),
                        ),
                    )
                    distance = min(
                        distance,
                        (
                            (px - ax - ratio * (bx - ax)) ** 2
                            + (py - ay - ratio * (by - ay)) ** 2
                        )
                        ** 0.5,
                    )
                color = (125, 226, 180) if distance < 0.035 else (16, 25, 35)
                pixels.extend((color[2], color[1], color[0], 255))
        mask = bytes(((size + 31) // 32) * 4 * size)
        header = struct.pack(
            "<IIIHHIIIIII", 40, size, size * 2, 1, 32, 0, len(pixels), 0, 0, 0, 0
        )
        images.append((size, header + pixels + mask))
    offset = 6 + 16 * len(images)
    entries = []
    for size, data in images:
        entries.append(
            struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(data), offset)
        )
        offset += len(data)
    path = Path(__file__).resolve().parent.parent / "lagcheck" / "resources" / "app.ico"
    path.write_bytes(
        struct.pack("<HHH", 0, 1, len(images))
        + b"".join(entries)
        + b"".join(data for _, data in images)
    )


if __name__ == "__main__":
    main()
