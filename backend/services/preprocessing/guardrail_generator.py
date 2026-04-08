"""Generate healthcare-ai-guardrails YAML from a dataset fingerprint.

The generated YAML constrains inference inputs to remain within the training
data distribution using the healthcare-ai-guardrails validator library.
Validators are parameterised with percentile-based bounds derived from the
fingerprint so that reasonable out-of-distribution studies are flagged.
"""

import logging
from pathlib import Path

import yaml  # PyYAML is a transitive dependency of many packages

logger = logging.getLogger(__name__)

# Margin factor applied to percentile bounds — widens thresholds slightly
# beyond the observed p05/p95 to tolerate minor real-world variation.
_MARGIN = 0.15


class GuardrailGenerator:
    """Convert a DatasetFingerprint into a healthcare-ai-guardrails YAML config."""

    def generate(
        self,
        fingerprint: dict,
        guardrail_name: str = "rt_pipeline_guardrails",
        modalities: list[str] | None = None,
    ) -> str:
        """Build and return the YAML string for the given fingerprint.

        Args:
            fingerprint: dict as returned by DatasetFingerprinter.compute()
                         (or stored in DatasetFingerprint columns).
            guardrail_name: Human-readable name embedded in the YAML.
            modalities: List of DICOM modalities to allow (e.g. ["MR", "CT"]).
                        Defaults to ["MR"] if not specified.
        """
        allowed_modalities = modalities or fingerprint.get("modalities") or ["MR"]

        input_validators = []
        output_validators = []

        # --- Modality check ---
        if allowed_modalities:
            input_validators.append({
                "type": "dicom_modality",
                "allowed": allowed_modalities,
            })

        # --- Pixel spacing (in-plane, xy) ---
        sp_p05 = fingerprint.get("spacing_p05", [0.5, 0.5, 1.0])
        sp_p95 = fingerprint.get("spacing_p95", [1.5, 1.5, 5.0])
        if sp_p05 and sp_p95:
            margin_xy = max(sp_p05[0], sp_p95[0]) * _MARGIN
            input_validators.append({
                "type": "dicom_pixel_spacing",
                "min_mm": round(max(0.01, sp_p05[0] - margin_xy), 4),
                "max_mm": round(sp_p95[0] + margin_xy, 4),
            })

        # --- Slice thickness (z spacing) ---
        if len(sp_p05) >= 3 and len(sp_p95) >= 3:
            margin_z = max(sp_p05[2], sp_p95[2]) * _MARGIN
            input_validators.append({
                "type": "dicom_slice_thickness",
                "min_mm": round(max(0.01, sp_p05[2] - margin_z), 4),
                "max_mm": round(sp_p95[2] + margin_z, 4),
            })

        # --- Intensity range (mapped to DICOM rescale intercept / window) ---
        i_p05 = fingerprint.get("intensity_p05")
        i_p95 = fingerprint.get("intensity_p95")
        if i_p05 is not None and i_p95 is not None:
            i_range = i_p95 - i_p05
            margin_i = i_range * _MARGIN
            input_validators.append({
                "type": "numeric_range",
                "field": "intensity_p05",
                "min": round(i_p05 - margin_i, 2),
                "max": round(i_p95 + margin_i, 2),
                "description": (
                    "5th-percentile voxel intensity should fall within the training range"
                ),
            })

        # --- Image dimension bounds ---
        size_min = fingerprint.get("size_min", [32, 32, 8])
        size_max = fingerprint.get("size_max", [1024, 1024, 512])
        if size_min and size_max:
            input_validators.append({
                "type": "numeric_range",
                "field": "image_dimensions",
                "description": (
                    f"Expected image sizes (voxels): "
                    f"min {size_min}, max {size_max}"
                ),
                "min_voxels": size_min,
                "max_voxels": size_max,
            })

        # --- Output: RT structure check ---
        output_validators.append({
            "type": "rt_structure_check",
            "description": "Generated RTSTRUCT must contain at least one ROI",
            "min_rois": 1,
        })

        spec = {
            "name": guardrail_name,
            "version": "1.0",
            "description": (
                f"Auto-generated from dataset fingerprint. "
                f"Training set: {fingerprint.get('n_images', '?')} images, "
                f"median spacing {fingerprint.get('spacing_median', '?')} mm."
            ),
            "input": input_validators,
            "output": output_validators,
        }

        yaml_str = yaml.dump(spec, default_flow_style=False, sort_keys=False)
        logger.info("Guardrail YAML generated", extra={"name": guardrail_name})
        return yaml_str

    def save(self, yaml_content: str, output_path: str) -> str:
        """Write YAML to disk and return the path."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml_content, encoding="utf-8")
        logger.info("Guardrail YAML saved", extra={"path": str(path)})
        return str(path)
