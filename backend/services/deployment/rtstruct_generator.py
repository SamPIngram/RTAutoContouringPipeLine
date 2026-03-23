import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class RtStructGenerator:
    """Generate DICOM RTSTRUCT from NIfTI mask predictions using rt-utils.

    Also handles routing the generated RTSTRUCT to the configured destination
    (Orthanc → TPS, local folder, or user download).
    """

    def run(
        self,
        input_nifti_path: str,
        model_id: str,
        hardware: str = "cpu",
        output_dir: str = "/data/rtstruct",
    ) -> dict:
        """Run inference with the specified model and generate RTSTRUCT.

        This method:
        1. Locates the model prediction NIfTI outputs.
        2. Converts masks to DICOM RTSTRUCT via rt-utils.
        3. Returns metadata including the path to the generated file.
        """
        input_path = Path(input_nifti_path)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        rtstruct_path = out_dir / f"{input_path.stem}_rtstruct.dcm"

        # Run model inference (delegated to the appropriate runner)
        prediction_nifti = self._run_model(input_nifti_path, model_id, hardware)

        # Convert prediction to RTSTRUCT
        self._nifti_to_rtstruct(
            prediction_nifti=prediction_nifti,
            reference_dicom_dir=str(input_path.parent),
            output_path=str(rtstruct_path),
        )

        logger.info(
            "RTSTRUCT generated",
            extra={"path": str(rtstruct_path), "model_id": model_id},
        )
        return {"rtstruct_path": str(rtstruct_path), "status": "generated"}

    def _run_model(self, input_nifti_path: str, model_id: str, hardware: str) -> str:
        """Run the model and return the path to the prediction NIfTI."""
        from backend.services.training.nnunet import NnUNetRunner

        runner = NnUNetRunner()
        input_dir = Path(input_nifti_path).parent
        output_dir = Path(f"/data/predictions/{model_id}")

        runner.predict(
            input_dir=input_dir,
            output_dir=output_dir,
            config={"model_id": model_id},
        )
        # Return first prediction file found
        predictions = list(output_dir.glob("*.nii.gz"))
        if not predictions:
            raise FileNotFoundError(f"No predictions found in {output_dir}")
        return str(predictions[0])

    @staticmethod
    def _nifti_to_rtstruct(
        prediction_nifti: str,
        reference_dicom_dir: str,
        output_path: str,
    ) -> None:
        """Convert a NIfTI segmentation mask to a DICOM RTSTRUCT using rt-utils."""
        try:
            from rt_utils import RTStructBuilder  # type: ignore[import]
        except ImportError:
            raise RuntimeError("rt-utils not installed. Run: uv add rt-utils")

        import SimpleITK as sitk  # type: ignore[import]
        import numpy as np

        rtstruct = RTStructBuilder.create_new(dicom_series_path=reference_dicom_dir)
        mask_image = sitk.ReadImage(prediction_nifti)
        mask_array = sitk.GetArrayFromImage(mask_image).astype(bool)

        # Transpose from SimpleITK (z,y,x) to rt-utils expected (x,y,z)
        mask_array = np.transpose(mask_array, (2, 1, 0))
        rtstruct.add_roi(mask=mask_array, name="AI_Contour")
        rtstruct.save(output_path)

    def export_to_orthanc(self, rtstruct_path: str) -> str:
        """Send the RTSTRUCT to Orthanc for routing to the TPS."""
        from backend.config import load_settings
        from backend.services.ingestion.orthanc import OrthancService

        settings = load_settings(os.environ.get("CONFIG_PATH", "config.toml"))
        svc = OrthancService(
            settings.orthanc.url,
            settings.orthanc.username,
            settings.orthanc.password,
        )
        instance_id = svc.send_file(rtstruct_path)
        logger.info("RTSTRUCT sent to Orthanc", extra={"instance_id": instance_id})
        return instance_id
