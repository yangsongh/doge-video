#!/usr/bin/env python3
"""
convert_video.py - convert videos into the format expected by Doge Video.

Target:
  H.264 High, 960x540, 15 fps, yuv420p, AAC LC 44.1 kHz stereo, faststart.

Usage:
  python tools/convert_video.py <file-or-directory> [--output DIR] [--push]

If --push is given, the converted files are copied to
/userdisk/Favorite/Video on the connected DictPen via adb.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".m4v", ".ts"}
DEVICE_DIR = "/userdisk/Favorite/Video"
FILTER = (
    "scale=960:540:force_original_aspect_ratio=decrease,"
    "pad=960:540:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=15"
)


def find_ffmpeg(explicit=None):
    if explicit:
        return explicit
    return shutil.which("ffmpeg")


def safe_stem(path):
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", path.stem).strip("_")
    if not stem:
        stem = "video"
    return stem[:60]


def collect_inputs(input_path):
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        return sorted(
            p for p in input_path.rglob("*")
            if p.is_file() and p.suffix.lower() in VIDEO_EXTS
        )
    return []


def convert_one(ffmpeg, src, dst):
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-map", "0:v:0", "-map", "0:a:0?",
        "-vf", FILTER,
        "-c:v", "libx264",
        "-profile:v", "high",
        "-level", "3.1",
        "-pix_fmt", "yuv420p",
        "-b:v", "600k",
        "-maxrate", "800k",
        "-bufsize", "1600k",
        "-c:a", "aac",
        "-b:a", "96k",
        "-ar", "44100",
        "-ac", "2",
        "-movflags", "+faststart",
        "-shortest",
        str(dst),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        return False, proc.stderr.decode("utf-8", "replace").strip()
    return True, ""


def push_to_device(output_dir, names):
    if not names:
        return
    subprocess.run(["adb", "shell", "mkdir", "-p", DEVICE_DIR], check=False)
    for name in names:
        local = output_dir / name
        remote = DEVICE_DIR + "/" + name
        print(f"push {local} -> {remote}")
        subprocess.run(["adb", "push", str(local), remote], check=False)


def main():
    parser = argparse.ArgumentParser(
        description="Convert videos for Doge Video (H.264 High / 960x540 / 15fps / AAC)"
    )
    parser.add_argument("input", help="video file or directory")
    parser.add_argument(
        "--output", "-o", default="converted",
        help="output directory (default: ./converted)"
    )
    parser.add_argument(
        "--ffmpeg", default=None,
        help="path to ffmpeg (default: search PATH)"
    )
    parser.add_argument(
        "--push", action="store_true",
        help="push converted files to /userdisk/Favorite/Video via adb"
    )
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"input not found: {input_path}", file=sys.stderr)
        return 1

    ffmpeg = find_ffmpeg(args.ffmpeg)
    if not ffmpeg:
        print(
            "ffmpeg not found. Install ffmpeg or pass --ffmpeg <path>.\n"
            "Windows: https://www.gyan.dev/ffmpeg/builds/  (essentials build)",
            file=sys.stderr,
        )
        return 1

    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs = collect_inputs(input_path)
    if not inputs:
        print("no supported video files found", file=sys.stderr)
        return 1

    print(f"ffmpeg: {ffmpeg}")
    print(f"output: {output_dir}")
    print(f"files : {len(inputs)}")

    converted = []
    failed = []

    for index, src in enumerate(inputs, 1):
        name = f"{index:03d}_{safe_stem(src)}.mp4"
        dst = output_dir / name
        print(f"[{index}/{len(inputs)}] {src.name} -> {name}")
        ok, err = convert_one(ffmpeg, src, dst)
        if ok:
            converted.append(name)
        else:
            failed.append((src.name, err))
            print(f"  failed: {err[:400]}", file=sys.stderr)

    print(f"\ndone: {len(converted)} converted, {len(failed)} failed")
    if converted:
        print(f"copy {output_dir} to {DEVICE_DIR} on the DictPen")
        if args.push:
            push_to_device(output_dir, converted)

    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
