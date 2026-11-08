from oneclick_cover import system_check


def _info(**overrides):
    info = {
        "platform": "Windows-11",
        "machine": "AMD64",
        "cpu_threads": 16,
        "ram_bytes": 32 * 1024 ** 3,
        "free_disk_bytes": 200 * 1024 ** 3,
        "nvidia_driver": True,
        "missing_assets": [],
    }
    info.update(overrides)
    return info


def test_report_for_capable_machine_has_no_warnings():
    report = system_check.format_system_report(_info())
    assert "32.0 GB" in report
    assert "No problems detected" in report


def test_report_warns_on_low_ram_disk_no_gpu_and_missing_assets():
    report = system_check.format_system_report(
        _info(
            ram_bytes=6 * 1024 ** 3,
            free_disk_bytes=2 * 1024 ** 3,
            nvidia_driver=False,
            missing_assets=["assets/rmvpe/rmvpe.pt"],
        )
    )
    assert "Less than 8 GB RAM" in report
    assert "Less than 10 GB free disk" in report
    assert "No NVIDIA GPU driver" in report
    assert "assets/rmvpe/rmvpe.pt" in report


def test_report_handles_unknown_values():
    report = system_check.format_system_report(
        _info(ram_bytes=None, free_disk_bytes=None, cpu_threads=None)
    )
    assert "RAM: unknown" in report
    assert "CPU threads: unknown" in report
