# ml/

The current frozen baseline for rooftop/building segmentation is Model M: STT with a ResNet-50 backbone and the INRIA checkpoint. Its engineering selection and inference validation are documented in [`docs/MODEL_SELECTION_JOURNEY.md`](../docs/MODEL_SELECTION_JOURNEY.md).

Phase 6 integrates baseline inference, preprocessing, tiling, mask reconstruction, and the validated imagery input contract. Phase 7 covers quantitative evaluation where labeled ground truth exists, plus optional U-Net training, Model M fine-tuning, and model comparison. U-Net training is not a prerequisite for the first working inference pipeline.

The real TIFF at `data/test/naip/cedar_park_residential.tif` is a local test fixture, not NAIP acquisition integration. Do not present visual detections as formal accuracy metrics. Verify model repository, checkpoint, and dataset terms before redistribution or deployment.

GPU/CUDA wheel choices and device behavior must follow `ENVIRONMENT_SETUP.md` and `AGENT_RULES.md`.
