from abc import ABC, abstractmethod
from pathlib import Path


class BaseModelRunner(ABC):
    """Base class for all model inference runners.

    Subclasses implement framework-specific inference:
    - NnUNetRunner (nnU-Net v2)
    - MonaiRunner (MONAI-based models)
    - CustomRunner (arbitrary PyTorch models)
    """

    @abstractmethod
    def predict(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        config: dict,
    ) -> Path:
        """Run inference.

        Args:
            input_dir: Directory containing NIfTI input files.
            output_dir: Directory to write prediction NIfTI files.
            config: Deployment inference configuration dict.

        Returns:
            Path to the output directory containing predictions.
        """

    @property
    def framework_name(self) -> str:
        raise NotImplementedError
