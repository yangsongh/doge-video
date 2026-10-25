#!/usr/bin/env python3
"""
Doge Video Converter - a small GUI for converting videos to the format
required by the DictPen system video player.

Target: H.264 High / 960x540 / 15fps / yuv420p / AAC 44.1 kHz stereo / faststart.

The Windows executable bundles ffmpeg, so users do not need Python or ffmpeg.
"""

import argparse
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

APP_TITLE = "Doge 视频转码工具"
TARGET_TEXT = "输出规格：H.264 High / 960×540 / 15fps / AAC 44.1kHz"
DEVICE_DIR = "/userdisk/Favorite/Video"
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".m4v", ".ts"}
FILTER = (
    "scale=960:540:force_original_aspect_ratio=decrease,"
    "pad=960:540:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=15"
)
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def resource_path(name):
    candidates = []
    if getattr(sys, "_MEIPASS", None):
        candidates.append(Path(sys._MEIPASS) / name)
    candidates.append(Path(__file__).resolve().parent / name)
    candidates.append(Path(sys.executable).resolve().parent / name)
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def find_ffmpeg():
    env = os.environ.get("DOGE_FFMPEG")
    if env and Path(env).exists():
        return env
    for name in ("ffmpeg.exe", "ffmpeg"):
        path = resource_path(name)
        if path:
            return path
    return shutil.which("ffmpeg")


def find_adb():
    return shutil.which("adb")


def collect_inputs(files, folder):
    paths = []
    if files:
        paths = [Path(p) for p in files]
    elif folder:
        root = Path(folder)
        if root.is_dir():
            paths = sorted(
                p for p in root.rglob("*")
                if p.is_file() and p.suffix.lower() in VIDEO_EXTS
            )
    return [p for p in paths if p.suffix.lower() in VIDEO_EXTS]


def safe_stem(path):
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", path.stem).strip("_")
    if not stem:
        stem = "video"
    return stem[:60]


def probe_duration(ffmpeg, src):
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", str(src)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            creationflags=CREATE_NO_WINDOW,
        )
        match = re.search(
            r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
            proc.stderr or "",
        )
        if not match:
            return None
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = float(match.group(3))
        return hours * 3600 + minutes * 60 + seconds
    except Exception:
        return None


def convert_one(ffmpeg, src, dst, on_progress, stop_event):
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-progress", "pipe:1", "-nostats",
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

    duration = probe_duration(ffmpeg, src)
    errors = []

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception as exc:
        return False, f"无法启动 ffmpeg：{exc}"

    for line in proc.stdout:
        if stop_event.is_set():
            try:
                proc.terminate()
            except Exception:
                pass
            break

        line = line.strip()
        if not line:
            continue

        if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
            try:
                micros = int(line.split("=", 1)[1])
                if duration and on_progress:
                    on_progress(min(0.99, micros / 1000000.0 / duration))
            except Exception:
                pass
        elif line.startswith("progress=end"):
            if on_progress:
                on_progress(1.0)
        elif not line.startswith((
            "frame=", "fps=", "bitrate=", "total_size=", "out_time",
            "dup_frames=", "drop_frames=", "speed=", "progress=",
        )):
            errors.append(line)

    code = proc.wait()
    if stop_event.is_set():
        return False, "已停止"
    if code != 0:
        detail = "\n".join(errors[-8:]) or f"ffmpeg 退出码 {code}"
        return False, detail
    return True, ""


def push_to_device(files, output_dir):
    adb = find_adb()
    if not adb:
        return False, "电脑上没有找到 adb。可以手动把转换后的文件复制到词典笔的 /userdisk/Favorite/Video。"

    try:
        check = subprocess.run(
            [adb, "devices"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=20, creationflags=CREATE_NO_WINDOW,
        )
        devices = [
            line.split("\t")[0]
            for line in (check.stdout or "").splitlines()
            if "\tdevice" in line
        ]
        if not devices:
            return False, "没有检测到词典笔。请连接 USB、打开 ADB，然后重试。"
        subprocess.run(
            [adb, "shell", "mkdir", "-p", DEVICE_DIR],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=20, creationflags=CREATE_NO_WINDOW,
        )
        for path in files:
            path = Path(path)
            # Push to an explicit destination file, not just a directory.
            # Some adb versions mishandle a directory argument with a trailing
            # slash and can drop the extension from the local filename.
            name = path.name
            if not name.lower().endswith(".mp4"):
                name += ".mp4"
            remote = DEVICE_DIR + "/" + name
            result = subprocess.run(
                [adb, "push", str(path), remote],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=120, creationflags=CREATE_NO_WINDOW,
            )
            if result.returncode != 0:
                return False, f"推送失败：{name}\n{(result.stderr or result.stdout or '').strip()}"
        return True, f"已推送到词典笔 {DEVICE_DIR}"
    except Exception as exc:
        return False, f"adb 推送失败：{exc}"


class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("900x820")
        self.root.minsize(760, 700)

        self.input_files = []
        self.input_dir = None
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        self.running = False
        self.proc = None
        self.converted = []
        self.failed = []
        self.output_dir = None

        self.ffmpeg = find_ffmpeg()
        self.adb = find_adb()

        self._build_style()
        self._build_ui()
        self._poll()

    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            try:
                style.theme_use("clam")
            except Exception:
                pass
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=6)
        style.configure("TLabel", font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 20, "bold"))
        style.configure("Sub.TLabel", font=("Microsoft YaHei UI", 10))
        style.configure("Start.TButton", font=("Microsoft YaHei UI", 12, "bold"), padding=10)

    def _build_ui(self):
        header = ttk.Frame(self.root, padding=(18, 14, 18, 4))
        header.pack(fill="x")
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="把视频转换成词典笔能播放的格式。",
            style="Sub.TLabel",
            wraplength=840,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

        input_frame = ttk.LabelFrame(self.root, text=" 1. 选择视频 ", padding=10)
        input_frame.pack(fill="x", padx=18, pady=(10, 4))

        self.input_var = tk.StringVar(value="还没有选择视频")
        ttk.Entry(input_frame, textvariable=self.input_var, state="readonly").pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ttk.Button(input_frame, text="选择文件", command=self.choose_files).pack(side="left", padx=2)
        ttk.Button(input_frame, text="选择文件夹", command=self.choose_folder).pack(side="left", padx=2)

        output_frame = ttk.LabelFrame(self.root, text=" 2. 保存到 ", padding=10)
        output_frame.pack(fill="x", padx=18, pady=4)

        default_output = Path.home() / "Videos" / "Doge视频"
        self.output_var = tk.StringVar(value=str(default_output))
        ttk.Entry(output_frame, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ttk.Button(output_frame, text="浏览", command=self.choose_output).pack(side="left")

        option_frame = ttk.Frame(self.root, padding=(18, 4, 18, 2))
        option_frame.pack(fill="x")

        self.push_var = tk.BooleanVar(value=bool(self.adb))
        self.open_var = tk.BooleanVar(value=True)

        self.push_check = ttk.Checkbutton(
            option_frame,
            text="转换完成后自动推送到词典笔（需要 adb）",
            variable=self.push_var,
        )
        self.push_check.pack(anchor="w")
        if not self.adb:
            self.push_check.state(["disabled"])
            self.push_var.set(False)

        ttk.Checkbutton(
            option_frame,
            text="转换完成后打开输出文件夹",
            variable=self.open_var,
        ).pack(anchor="w", pady=(2, 0))

        ttk.Label(option_frame, text=TARGET_TEXT, foreground="#555555").pack(anchor="w", pady=(4, 0))

        action_frame = ttk.Frame(self.root, padding=(18, 8, 18, 2))
        action_frame.pack(fill="x")

        self.start_button = ttk.Button(
            action_frame, text="开始转换", command=self.start, style="Start.TButton"
        )
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(
            action_frame, text="停止", command=self.stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=8)
        self.open_button = ttk.Button(
            action_frame, text="打开输出文件夹", command=self.open_output
        )
        self.open_button.pack(side="left")

        progress_frame = ttk.Frame(self.root, padding=(18, 8, 18, 2))
        progress_frame.pack(fill="x")
        self.progress = ttk.Progressbar(
            progress_frame, orient="horizontal", mode="determinate", maximum=100
        )
        self.progress.pack(side="left", fill="x", expand=True)
        self.progress_text = ttk.Label(progress_frame, text="等待开始", width=20)
        self.progress_text.pack(side="left", padx=(10, 0))

        log_frame = ttk.LabelFrame(self.root, text=" 日志 ", padding=6)
        log_frame.pack(fill="both", expand=True, padx=18, pady=(6, 4))
        self.log = ScrolledText(log_frame, height=8, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

        self.log.configure(state="normal")
        self.log.insert(
            "end",
            "选择视频后点“开始转换”。\n"
            "转换会重新编码，10 分钟视频大约需要几分钟；文件名会自动改成英文数字。\n",
        )
        self.log.configure(state="disabled")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def choose_files(self):
        files = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.mov *.mkv *.avi *.webm *.flv *.m4v *.ts"),
                ("所有文件", "*.*"),
            ],
        )
        if not files:
            return
        self.input_files = list(files)
        self.input_dir = None
        self.input_var.set(f"已选择 {len(self.input_files)} 个文件")
        self.append_log("选择文件：")
        for path in self.input_files:
            self.append_log("  " + Path(path).name)

    def choose_folder(self):
        folder = filedialog.askdirectory(title="选择视频文件夹")
        if not folder:
            return
        self.input_dir = folder
        self.input_files = []
        self.input_var.set(f"已选择文件夹：{folder}")
        self.append_log("选择文件夹：" + folder)

    def choose_output(self):
        folder = filedialog.askdirectory(title="选择输出文件夹")
        if folder:
            self.output_var.set(folder)

    def start(self):
        if self.running:
            return

        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            messagebox.showerror(
                APP_TITLE,
                "没有找到 ffmpeg。\n请使用打包好的 exe，或把 ffmpeg.exe 放到程序旁边。",
            )
            return

        files = collect_inputs(self.input_files, self.input_dir)
        if not files:
            messagebox.showwarning(APP_TITLE, "请先选择视频文件或包含视频的文件夹。")
            return

        output = Path(self.output_var.get().strip())
        if not output:
            messagebox.showwarning(APP_TITLE, "请选择输出文件夹。")
            return
        try:
            output.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"无法创建输出文件夹：{exc}")
            return

        self.output_dir = output
        self.converted = []
        self.failed = []
        self.stop_event.clear()
        self.running = True
        self.progress["value"] = 0
        self.progress_text.configure(text="准备中...")
        self.start_button.state(["disabled"])
        self.stop_button.state(["!disabled"])
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.append_log(f"共 {len(files)} 个视频，输出到：{output}")

        thread = threading.Thread(
            target=self._worker, args=(files, output, ffmpeg), daemon=True
        )
        thread.start()

    def _worker(self, files, output, ffmpeg):
        total = len(files)
        converted = []
        failed = []

        for index, src in enumerate(files, 1):
            if self.stop_event.is_set():
                break

            dst = output / f"{index:03d}_{safe_stem(src)}.mp4"
            self.queue.put(("log", f"[{index}/{total}] {src.name} -> {dst.name}"))

            def on_progress(fraction, index=index, total=total):
                value = ((index - 1) + max(0.0, min(1.0, fraction))) / total * 100
                self.queue.put(("progress", value))

            ok, error = convert_one(ffmpeg, src, dst, on_progress, self.stop_event)
            if self.stop_event.is_set():
                break

            if ok:
                converted.append(dst)
                self.queue.put(("log", "  完成"))
            else:
                failed.append((src, error))
                self.queue.put(("log", "  失败：" + error.replace("\n", " | ")))
            self.queue.put(("progress", index / total * 100))

        self.queue.put(("done", converted, failed, self.stop_event.is_set()))
        if self.push_var.get() and converted and not self.stop_event.is_set():
            self.queue.put(("log", "正在推送到词典笔..."))
            ok, message = push_to_device(converted, output)
            self.queue.put(("log", message))
            self.queue.put(("push_done", ok, message))

    def _poll(self):
        try:
            while True:
                item = self.queue.get_nowait()
                kind = item[0]

                if kind == "log":
                    self.append_log(item[1])
                elif kind == "progress":
                    self.progress["value"] = item[1]
                    self.progress_text.configure(text=f"{item[1]:.0f}%")
                elif kind == "done":
                    self.converted, self.failed, stopped = item[1], item[2], item[3]
                    self._finish(stopped)
                elif kind == "push_done":
                    if not item[1]:
                        messagebox.showwarning(APP_TITLE, item[2])
        except queue.Empty:
            pass

        self.root.after(100, self._poll)

    def _finish(self, stopped):
        self.running = False
        self.start_button.state(["!disabled"])
        self.stop_button.state(["disabled"])
        self.progress_text.configure(text="已停止" if stopped else "完成")
        if self.output_dir and self.open_var.get() and not stopped and self.converted:
            self.open_output()
        if stopped:
            return
        if self.failed:
            messagebox.showwarning(
                APP_TITLE,
                f"完成：{len(self.converted)} 个成功，{len(self.failed)} 个失败。\n详情看日志。",
            )
        elif self.converted:
            messagebox.showinfo(
                APP_TITLE,
                f"转换完成，共 {len(self.converted)} 个文件。\n"
                f"已保存到：{self.output_dir}\n"
                "请把文件放到词典笔的 /userdisk/Favorite/Video。",
            )

    def stop(self):
        if not self.running:
            return
        self.stop_event.set()
        self.append_log("正在停止...")
        self.progress_text.configure(text="停止中...")

    def open_output(self):
        path = Path(self.output_var.get().strip())
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            if os.name == "nt":
                os.startfile(str(path))
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception:
            messagebox.showinfo(APP_TITLE, f"输出文件夹：{path}")

    def on_close(self):
        if self.running:
            if not messagebox.askyesno(APP_TITLE, "正在转换，确定要退出吗？"):
                return
            self.stop_event.set()
        self.root.destroy()


def run_headless(input_path, output_path, ffmpeg):
    ffmpeg = ffmpeg or find_ffmpeg()
    src = Path(input_path)
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / "conversion.log"

    with open(log_path, "w", encoding="utf-8"):
        pass

    def say(message):
        if sys.stdout is not None:
            print(message)
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(message + "\n")

    if not ffmpeg:
        say("ffmpeg not found")
        return 1

    files = collect_inputs([str(src)] if src.is_file() else [], str(src) if src.is_dir() else None)
    if not files:
        say("no video files")
        return 1

    stop_event = threading.Event()
    failed = 0
    for index, path in enumerate(files, 1):
        dst = output / f"{index:03d}_{safe_stem(path)}.mp4"
        say(f"[{index}/{len(files)}] {path.name} -> {dst.name}")
        ok, error = convert_one(ffmpeg, path, dst, lambda fraction: None, stop_event)
        if ok:
            say("  done")
        else:
            failed += 1
            say("  failed: " + error)
    say(f"finished: {len(files) - failed} ok, {failed} failed")
    return 0 if failed == 0 else 2


def main():
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--headless", nargs=2, metavar=("INPUT", "OUTPUT"), help="no GUI, convert input to output")
    parser.add_argument("--ffmpeg", default=None, help="path to ffmpeg")
    args = parser.parse_args()

    if args.headless:
        raise SystemExit(run_headless(args.headless[0], args.headless[1], args.ffmpeg))

    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
