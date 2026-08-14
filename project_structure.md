# EmergencyIQ — Project Structure

This document describes the repository layout for EmergencyIQ: an AI-powered emergency call prioritization and smart dispatch management platform. The repository separates production services (backend, frontend) from research artifacts (datasets, training, models, results, documentation) to keep the codebase clean and reproducible.

Top-level layout:

- backend/ (existing)
  - Production FastAPI backend and deployment artifacts. Leave unchanged.

- frontend/ (existing)
  - Production React + Vite frontend. Leave unchanged.

- datasets/
  - raw/: Original, immutable datasets.
  - processed/: Cleaned / preprocessed data.
  - train/, validation/, test/: Dataset splits.
  - metadata/: Data dictionaries, licenses, provenance.

- training/
  - notebooks/: Jupyter notebooks for experiments.
  - preprocessing/, feature_engineering/, augmentation/: Pipelines and modules.
  - configs/, scripts/, utilities/: Experiment reproducibility artifacts.
  - checkpoints/, logs/: Model checkpoints and training logs.

- trained_models/
  - Per-task model directories plus exported and best_models.

- research_results/
  - Stored metrics, plots, benchmark and profiling outputs.

- documentation/
  - dissertation/, research_papers/, architecture/, diagrams/, API/, references/.

Notes:
- Do not commit large binary checkpoints to git; use external storage and reference URIs in the trained_models/README.md.
- Keep notebooks and scripts small and modular; prefer reproducible experiment configs.
- Follow the README in each major folder for usage details and conventions.
