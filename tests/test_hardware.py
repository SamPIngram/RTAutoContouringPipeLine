from unittest.mock import MagicMock, patch

from backend.hardware import probe_hardware, warn_if_no_gpu


class TestProbeHardware:
    def test_no_nvidia_smi(self):
        """Returns safe defaults when nvidia-smi is absent."""
        with patch("backend.hardware.shutil.which", return_value=None):
            info = probe_hardware()
        assert info["cuda_available"] is False
        assert info["gpu_count"] == 0
        assert info["gpu_names"] == []

    def test_gpu_detected(self):
        """Parses nvidia-smi output and populates hardware info."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "NVIDIA A100 80GB PCIe\nNVIDIA A100 80GB PCIe\n"

        with (
            patch("backend.hardware.shutil.which", return_value="/usr/bin/nvidia-smi"),
            patch("backend.hardware.subprocess.run", return_value=mock_result),
        ):
            info = probe_hardware()

        assert info["cuda_available"] is True
        assert info["gpu_count"] == 2
        assert info["gpu_names"] == ["NVIDIA A100 80GB PCIe", "NVIDIA A100 80GB PCIe"]

    def test_nvidia_smi_nonzero_exit(self):
        """Treats non-zero exit code as no GPU available."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with (
            patch("backend.hardware.shutil.which", return_value="/usr/bin/nvidia-smi"),
            patch("backend.hardware.subprocess.run", return_value=mock_result),
        ):
            info = probe_hardware()

        assert info["cuda_available"] is False

    def test_warn_if_no_gpu_logs_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="backend.hardware"):
            warn_if_no_gpu("test_task")
        assert "CPU" in caplog.text or "degraded" in caplog.text
