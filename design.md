# System Design: Radiotherapy Auto-Contouring Pipeline

## 1. Executive Summary
This document outlines the architecture and design principles for an end-to-end radiotherapy auto-contouring platform. The system facilitates data ingestion, dataset curation, model training (e.g., nnU-Net), validation, and clinical deployment. It is designed as a modular, containerized microservices architecture with a strong emphasis on auditability, configuration as code (TOML), and flexible clinical integration.

## 2. Architectural Overview
The system employs a microservices architecture, deployable primarily via Docker, with support for bare-metal execution.

* **Frontend UI:** React/Vue.js Single Page Application (SPA).
* **Central API/Backend:** FastAPI (Python) for routing, orchestration, and UI serving.
* **Task Queue:** Celery + Redis for asynchronous, long-running tasks (conversion, training, inference).
* **DICOM Engine:** Orthanc, serving as the primary DICOM node (SCP/SCU) for reliable networking.
* **Database:** PostgreSQL (or SQLite for lightweight setups) to store cohort metadata, model registries, and audit logs.

## 3. Configuration & Clinical Workflows (TOML)
To allow users to create solutions that fit their specific clinical workflows, all pipeline configurations are defined in `TOML` files. The UI acts as a visual builder for these files.

* **Global Config (`config.toml`):** Defines system-wide settings (Orthanc credentials, GPU visibility limits, base directory paths).
* **Deployment Configs (`deployments/*.toml`):** Defines specific clinical triggers and actions.

**Example Deployment TOML:**
```toml
[workflow]
name = "Prostate_Routine_T2"
active = true
trigger = "orthanc_new_study" # Options: orthanc_new_study, folder_watch, api

[filtering]
modality = "MR"
series_description_regex = ".*t2.*tra.*"

[inference]
model_id = "nnunet_prostate_v1.2"
fallback_to_cpu = true # Allows CPU execution if GPU is saturated

[export]
generate_rtstruct = true
rtstruct_name = "AI_Prostate_Contours"
destination_type = "dicom_node" # Options: dicom_node, folder, download
destination_aet = "CLINICAL_TPS"
```

## 4. Core Modules

### 4.1. Data Ingestion & Integration
* **Orthanc Node:** Receives DICOM data from clinical systems. The API listens to Orthanc webhooks for new instances/studies.
* **Folder Watcher:** Background daemon monitoring local/network directories.
* **ProKnow Sync:** Periodic pulls via ProKnow SDK based on configured workspaces.

### 4.2. Data Preprocessing & UI
* **Dataset Builder:** UI to query the internal database (populated by Orthanc) to build training cohorts.
* **Conversion Engine:** Pipeline step to convert DICOM series to standard NIfTI formats, handling spatial resampling and orientation standardisation.

### 4.3. Model Training Orchestration
* **Framework Support:** Native integration for nnU-Net v2 and extensible base classes for custom PyTorch/MONAI models.
* **Container Spawning:** For heavy training jobs, the backend uses the Docker socket to spin up dedicated, ephemeral training containers mapped to the specific dataset and GPU.

### 4.4. Validation & Review
* **QA Pipeline:** Automated generation of geometric metrics (Dice, HD95).
* **Viewer:** Integrated web-viewer (e.g., NiiVue) overlaying NIfTI/DICOM with AI predictions vs. ground truth.

### 4.5. Small Deployment Framework
* **Execution:** A lightweight runner that loads a Deployment TOML. It listens for the specified trigger, runs data through the conversion engine, executes the inference container, and packages the result via rt-utils.
* **Routing:** Sends the generated RTSTRUCT back through Orthanc to push to the Treatment Planning System (TPS).

## 5. Logging, Auditing, and Post-Deployment Surveillance
Complete traceability is a core requirement for research and clinical translation.

* **Structured Logging:** All backend services output JSON-formatted logs containing timestamps, trace IDs, and event levels.
* **Audit Trail:** Every data movement (e.g., "DICOM imported", "Dataset exported", "Model trained on Patient X") is logged to the database with a user/system ID.
* **Post-Deployment Surveillance:**
  * The deployment framework logs all inference attempts.
  * **Failure Tracking:** Exceptions (e.g., "Failed to parse DICOM header", "CUDA Out of Memory") are captured, linked to the offending series UID, and flagged in the UI.
  * **Performance Metrics:** Inference time, hardware utilization, and trigger-to-export latency are recorded to monitor pipeline degradation over time.

## 6. Hardware Abstraction
* The system probes the host environment on startup.
* Tasks assigned to the Celery queue are tagged with hardware requirements (e.g., `requires_gpu`). Workers consume tasks based on their available hardware, ensuring smooth fallbacks to CPU processing where appropriate (though with a logged warning for inference speed).
