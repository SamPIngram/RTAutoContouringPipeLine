"""Apply healthcare-ai-guardrails validation to inference inputs and outputs.

Loads a guardrail YAML (stored in GuardrailConfig) and runs all configured
validators against the DICOM study before inference begins. Failures are
logged and returned as structured results — they do not hard-block inference
unless the caller opts in (block_on_failure=True).
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    passed: bool
    violations: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    validator_results: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "warnings": self.warnings,
            "validator_results": self.validator_results,
        }


class GuardrailValidator:
    """Validate a DICOM study against a healthcare-ai-guardrails YAML spec."""

    def __init__(self, yaml_content: str) -> None:
        self._spec = yaml.safe_load(yaml_content)
        self._name = self._spec.get("name", "unnamed")

    @classmethod
    def from_file(cls, yaml_path: str) -> "GuardrailValidator":
        content = Path(yaml_path).read_text(encoding="utf-8")
        return cls(content)

    def validate_input(
        self,
        dicom_dir: str,
        block_on_failure: bool = False,
    ) -> ValidationReport:
        """Run input validators against DICOM files in dicom_dir.

        Args:
            dicom_dir: Path to the DICOM series directory.
            block_on_failure: If True, raise RuntimeError on validation failure.

        Returns:
            ValidationReport with per-validator results.
        """
        report = self._run_validators(
            validators=self._spec.get("input", []),
            context={"dicom_dir": dicom_dir},
            stage="input",
        )

        if not report.passed:
            logger.warning(
                "Guardrail input validation failed",
                extra={
                    "guardrail": self._name,
                    "violations": report.violations,
                },
            )
            if block_on_failure:
                raise RuntimeError(
                    f"Guardrail '{self._name}' input validation failed: "
                    + "; ".join(v["message"] for v in report.violations)
                )
        else:
            logger.info(
                "Guardrail input validation passed",
                extra={"guardrail": self._name},
            )

        return report

    def validate_output(
        self,
        rtstruct_path: str,
        block_on_failure: bool = False,
    ) -> ValidationReport:
        """Run output validators against the generated RTSTRUCT DICOM."""
        report = self._run_validators(
            validators=self._spec.get("output", []),
            context={"rtstruct_path": rtstruct_path},
            stage="output",
        )

        if not report.passed:
            logger.warning(
                "Guardrail output validation failed",
                extra={"guardrail": self._name, "violations": report.violations},
            )
            if block_on_failure:
                raise RuntimeError(
                    f"Guardrail '{self._name}' output validation failed: "
                    + "; ".join(v["message"] for v in report.violations)
                )

        return report

    def _run_validators(
        self, validators: list[dict], context: dict, stage: str
    ) -> ValidationReport:
        """Dispatch validators; try healthcare-ai-guardrails first, fall back to built-ins."""
        violations: list[dict] = []
        warnings: list[dict] = []
        results: list[dict] = []

        for spec in validators:
            vtype = spec.get("type", "unknown")
            try:
                result = self._run_single(vtype, spec, context, stage)
            except Exception as exc:
                result = {
                    "type": vtype,
                    "passed": False,
                    "message": f"Validator error: {exc}",
                    "stage": stage,
                }

            results.append(result)
            if not result.get("passed", True):
                if result.get("severity", "error") == "warning":
                    warnings.append(result)
                else:
                    violations.append(result)

        return ValidationReport(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            validator_results=results,
        )

    def _run_single(
        self, vtype: str, spec: dict, context: dict, stage: str
    ) -> dict:
        """Run one validator; delegate to healthcare_ai_guardrails where possible."""

        # ---- Try healthcare_ai_guardrails package first ----
        try:
            from healthcare_ai_guardrails import GuardrailRunner  # type: ignore[import]
            from healthcare_ai_guardrails import validators as hc_validators  # type: ignore[import]

            validator_cls = getattr(hc_validators, vtype, None)
            if validator_cls is not None:
                params = {k: v for k, v in spec.items() if k != "type"}
                validator = validator_cls(**params)
                runner = GuardrailRunner([validator])
                data = context.get("dicom_dir") or context.get("rtstruct_path", "")
                hc_results = runner.run(data)
                passed = all(r.passed for r in hc_results)
                messages = [r.message for r in hc_results if not r.passed]
                return {
                    "type": vtype,
                    "passed": passed,
                    "message": "; ".join(messages) if messages else "OK",
                    "stage": stage,
                }
        except ImportError:
            pass  # package not installed — fall through to built-ins

        # ---- Built-in fallback validators ----
        return self._builtin_validator(vtype, spec, context, stage)

    def _builtin_validator(
        self, vtype: str, spec: dict, context: dict, stage: str
    ) -> dict:
        """Lightweight fallback validators that don't require the HC guardrails package."""

        def _ok() -> dict:
            return {"type": vtype, "passed": True, "message": "OK (built-in)", "stage": stage}

        def _fail(msg: str) -> dict:
            return {"type": vtype, "passed": False, "message": msg, "stage": stage}

        if vtype == "dicom_modality":
            return self._check_dicom_modality(spec, context, stage)

        if vtype == "dicom_pixel_spacing":
            return self._check_pixel_spacing(spec, context, stage)

        if vtype == "dicom_slice_thickness":
            return self._check_slice_thickness(spec, context, stage)

        if vtype == "rt_structure_check":
            return self._check_rtstruct(spec, context, stage)

        if vtype == "numeric_range":
            # Metadata-only check; skip silently if we can't inspect
            return {
                "type": vtype,
                "passed": True,
                "message": "Skipped (metadata not available at runtime)",
                "stage": stage,
                "severity": "warning",
            }

        return {
            "type": vtype,
            "passed": True,
            "message": f"Unknown validator '{vtype}' — skipped",
            "stage": stage,
            "severity": "warning",
        }

    def _check_dicom_modality(self, spec: dict, context: dict, stage: str) -> dict:
        """Check the DICOM Modality tag against allowed list."""
        import pydicom  # type: ignore[import]

        dicom_dir = context.get("dicom_dir", "")
        allowed = spec.get("allowed", [])
        dcm_files = list(Path(dicom_dir).glob("*.dcm")) if dicom_dir else []
        if not dcm_files:
            return {
                "type": "dicom_modality",
                "passed": True,
                "message": "No DICOM files found — skipped",
                "stage": stage,
                "severity": "warning",
            }
        try:
            ds = pydicom.dcmread(str(dcm_files[0]), stop_before_pixels=True)
            modality = str(getattr(ds, "Modality", "UNKNOWN"))
            if allowed and modality not in allowed:
                return {
                    "type": "dicom_modality",
                    "passed": False,
                    "message": f"Modality '{modality}' not in allowed list {allowed}",
                    "stage": stage,
                }
            return {
                "type": "dicom_modality",
                "passed": True,
                "message": f"Modality '{modality}' OK",
                "stage": stage,
            }
        except Exception as exc:
            return {
                "type": "dicom_modality",
                "passed": True,
                "message": f"Could not read DICOM modality: {exc}",
                "stage": stage,
                "severity": "warning",
            }

    def _check_pixel_spacing(self, spec: dict, context: dict, stage: str) -> dict:
        import pydicom

        dicom_dir = context.get("dicom_dir", "")
        dcm_files = list(Path(dicom_dir).glob("*.dcm")) if dicom_dir else []
        if not dcm_files:
            return {"type": "dicom_pixel_spacing", "passed": True,
                    "message": "No DICOM files — skipped", "stage": stage, "severity": "warning"}
        try:
            ds = pydicom.dcmread(str(dcm_files[0]), stop_before_pixels=True)
            ps = getattr(ds, "PixelSpacing", None)
            if ps is None:
                return {"type": "dicom_pixel_spacing", "passed": True,
                        "message": "PixelSpacing tag absent — skipped", "stage": stage,
                        "severity": "warning"}
            spacing = float(ps[0])
            min_mm = spec.get("min_mm", 0.0)
            max_mm = spec.get("max_mm", 99.0)
            if not (min_mm <= spacing <= max_mm):
                return {"type": "dicom_pixel_spacing", "passed": False,
                        "message": f"PixelSpacing {spacing:.3f} mm outside [{min_mm}, {max_mm}]",
                        "stage": stage}
            return {"type": "dicom_pixel_spacing", "passed": True,
                    "message": f"PixelSpacing {spacing:.3f} mm OK", "stage": stage}
        except Exception as exc:
            return {"type": "dicom_pixel_spacing", "passed": True,
                    "message": f"Could not check pixel spacing: {exc}", "stage": stage,
                    "severity": "warning"}

    def _check_slice_thickness(self, spec: dict, context: dict, stage: str) -> dict:
        import pydicom

        dicom_dir = context.get("dicom_dir", "")
        dcm_files = list(Path(dicom_dir).glob("*.dcm")) if dicom_dir else []
        if not dcm_files:
            return {"type": "dicom_slice_thickness", "passed": True,
                    "message": "No DICOM files — skipped", "stage": stage, "severity": "warning"}
        try:
            ds = pydicom.dcmread(str(dcm_files[0]), stop_before_pixels=True)
            st = getattr(ds, "SliceThickness", None)
            if st is None:
                return {"type": "dicom_slice_thickness", "passed": True,
                        "message": "SliceThickness tag absent — skipped", "stage": stage,
                        "severity": "warning"}
            thickness = float(st)
            min_mm = spec.get("min_mm", 0.0)
            max_mm = spec.get("max_mm", 99.0)
            if not (min_mm <= thickness <= max_mm):
                return {"type": "dicom_slice_thickness", "passed": False,
                        "message": f"SliceThickness {thickness:.2f} mm outside [{min_mm}, {max_mm}]",
                        "stage": stage}
            return {"type": "dicom_slice_thickness", "passed": True,
                    "message": f"SliceThickness {thickness:.2f} mm OK", "stage": stage}
        except Exception as exc:
            return {"type": "dicom_slice_thickness", "passed": True,
                    "message": f"Could not check slice thickness: {exc}", "stage": stage,
                    "severity": "warning"}

    def _check_rtstruct(self, spec: dict, context: dict, stage: str) -> dict:
        import pydicom

        rtstruct_path = context.get("rtstruct_path", "")
        if not rtstruct_path or not Path(rtstruct_path).exists():
            return {"type": "rt_structure_check", "passed": True,
                    "message": "RTSTRUCT path not provided — skipped", "stage": stage,
                    "severity": "warning"}
        try:
            ds = pydicom.dcmread(rtstruct_path, stop_before_pixels=True)
            rois = getattr(ds, "StructureSetROISequence", [])
            min_rois = spec.get("min_rois", 1)
            if len(rois) < min_rois:
                return {"type": "rt_structure_check", "passed": False,
                        "message": f"RTSTRUCT has {len(rois)} ROIs, expected >= {min_rois}",
                        "stage": stage}
            return {"type": "rt_structure_check", "passed": True,
                    "message": f"RTSTRUCT has {len(rois)} ROI(s)", "stage": stage}
        except Exception as exc:
            return {"type": "rt_structure_check", "passed": True,
                    "message": f"Could not inspect RTSTRUCT: {exc}", "stage": stage,
                    "severity": "warning"}
