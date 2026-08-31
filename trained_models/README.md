# Trained Models

This directory stores model checkpoints, exported artifacts, and production-ready model files for EmergencyIQ.

Subfolders:
- speech/: Models for speech recognition and related tasks.
- audio_event/: Models for audio event detection.
- classifier/: Emergency / non-emergency classifiers.
- severity/: Severity scoring models.
- embedding/: Embedding models for retrieval and similarity.
- dispatch/: Models for dispatch decision support.
- best_models/: Selected top-performing checkpoints.
- exported/: Exported / serialized models (ONNX, TorchScript, SavedModel).

Do not store large binary artifacts in version control; use external storage for large checkpoints.
