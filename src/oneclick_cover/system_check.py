"""Live hardware and storage diagnostics for the current machine."""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

from scripts.download_rvc_assets import missing_rvc_assets
from oneclick_cover.settings import ROOT

MIN_RAM_GB = 8
MIN_FREE_DISK_GB = 10


def _total_ram_bytes() -> int | None:
    try:
        if os.name == "nt":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
            return None
        return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, ValueError, OSError):
        return None


def collect_system_info(path: Path | None = None) -> dict:
    target = Path(path or ROOT)
    try:
        free_disk = shutil.disk_usage(target).free
    except OSError:
        free_disk = None
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_threads": os.cpu_count(),
        "ram_bytes": _total_ram_bytes(),
        "free_disk_bytes": free_disk,
        "nvidia_driver": shutil.which("nvidia-smi") is not None,
        "missing_assets": missing_rvc_assets(ROOT / "vendor" / "rvc"),
    }


def _gb(value: int | None) -> str:
    return "unknown" if value is None else f"{value / 1024 ** 3:.1f} GB"


def format_system_report(info: dict) -> str:
    lines = [
        "## System check",
        f"- OS: {info['platform']} ({info['machine']})",
        f"- CPU threads: {info['cpu_threads'] or 'unknown'}",
        f"- RAM: {_gb(info['ram_bytes'])}",
        f"- Free disk space here: {_gb(info['free_disk_bytes'])}",
        "- NVIDIA driver: " + ("detected" if info["nvidia_driver"] else "not detected (CPU mode)"),
    ]
    notes = []
    ram = info["ram_bytes"]
    if ram is not None and ram < MIN_RAM_GB * 1024 ** 3:
        notes.append(
            f"Less than {MIN_RAM_GB} GB RAM: separation or conversion may run out of memory. "
            "Try short songs."
        )
    disk = info["free_disk_bytes"]
    if disk is not None and disk < MIN_FREE_DISK_GB * 1024 ** 3:
        notes.append(f"Less than {MIN_FREE_DISK_GB} GB free disk space: installs and job folders may fail.")
    if not info["nvidia_driver"]:
        notes.append("No NVIDIA GPU driver found: expect slow processing, and training is impractical on CPU.")
    if info["missing_assets"]:
        notes.append(
            "Missing or damaged RVC support files: " + ", ".join(info["missing_assets"])
            + ". Run install.bat again to download and verify them."
        )
    if notes:
        lines += ["", "**Notes**"] + [f"- {note}" for note in notes]
    else:
        lines += ["", "No problems detected. This is a quick check, not a benchmark."]
    return "\n".join(lines)
