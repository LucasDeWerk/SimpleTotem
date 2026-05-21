import psutil

from models.schemas import CPUInfo, MemoryInfo, DiskInfo


def get_cpu_usage() -> CPUInfo:
    freq = psutil.cpu_freq()
    return CPUInfo(
        usage_percent=psutil.cpu_percent(interval=0.5),
        core_count=psutil.cpu_count(logical=True),
        frequency_mhz=freq.current if freq else 0.0,
    )


def get_memory_info() -> MemoryInfo:
    mem = psutil.virtual_memory()
    return MemoryInfo(
        total_mb=round(mem.total / 1024 ** 2, 2),
        available_mb=round(mem.available / 1024 ** 2, 2),
        used_mb=round(mem.used / 1024 ** 2, 2),
        usage_percent=mem.percent,
    )


def get_disk_info(path: str = "/") -> DiskInfo:
    disk = psutil.disk_usage(path)
    return DiskInfo(
        total_gb=round(disk.total / 1024 ** 3, 2),
        used_gb=round(disk.used / 1024 ** 3, 2),
        free_gb=round(disk.free / 1024 ** 3, 2),
        usage_percent=disk.percent,
    )

