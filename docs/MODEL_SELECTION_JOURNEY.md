# HelioScan - Model Selection Journey

## 1. Purpose

This document records the engineering decision behind HelioScan's first rooftop/building segmentation baseline. It preserves the experiments and configuration needed to reproduce the selection without presenting inference validation as an accuracy benchmark.

## 2. Original segmentation plan

The original product plan described a U-Net-based segmentation pipeline and a later U-Net training phase. That history is retained. The plan has since changed: HelioScan has selected an existing pretrained building-extraction model as its first inference baseline. U-Net remains a valid future training and comparison path, but it is not required before the first working segmentation integration.

## 3. Why pretrained segmentation models were investigated

The investigation aimed to avoid unnecessary from-scratch training if a suitable pretrained building model could be reproduced. A pretrained candidate could shorten the path to an inference pipeline, allow real imagery and target hardware to be exercised early, and provide a concrete baseline before committing to a larger dataset and training effort.

## 4. Candidate categories

The following are model categories considered for the first baseline; except for Model M, this record does not claim that a specific implementation in these categories was experimentally evaluated:

- U-Net and U-Net variants - originally planned; not recorded as experimentally trained or benchmarked in this investigation.
- DeepLab-style semantic segmentation - considered, not experimentally evaluated here.
- SegFormer or other transformer segmentation - considered, not experimentally evaluated here.
- Existing building-extraction models - investigated as a route to a pretrained building-segmentation baseline.
- STT / Sparse Token Transformer - experimentally validated as Model M below.

No performance ranking between untested candidates is implied.

## 5. Why the original U-Net plan was not used as the first baseline

U-Net remains suitable for later experimentation and training. It was not rejected for poor performance: no HelioScan U-Net training or accuracy test is claimed here. Model M offered an already pretrained building-extraction checkpoint that could be checked for exact compatibility and executed on the target GPU, allowing the inference path to be validated before a custom training pipeline was required.

## 6. Model M discovery

Model M is the KyanChen / BuildingExtraction repository implementation of an STT (Sparse Token Transformer) model with a ResNet-50 backbone and an INRIA pretrained checkpoint.

- Repository: https://github.com/KyanChen/BuildingExtraction
- Checkpoint: `INRIA_ckpt_latest.pt`
- Checkpoint epoch: 299
- Dataset/checkpoint context: INRIA

The repository implementation, configuration and preprocessing were inspected and reproduced during the investigation. Repository, checkpoint, and INRIA dataset license and redistribution terms must still be verified before redistribution or deployment.

## 7. Checkpoint compatibility investigation

The first attempted model configuration used `resnet50` with `out_keys = ['block5']` and did not match the checkpoint. Removing the DataParallel `module.` prefix from checkpoint keys did not resolve the mismatch; ResNet layer4 parameters remained missing.

A systematic output-stage check established:

| Configuration | Missing keys | Unexpected keys | Result |
| --- | ---: | ---: | --- |
| `resnet50` + `block5` | 62 | 0 | Incompatible |
| `resnet50` + `block4` | 0 | 0 | Exact checkpoint compatibility |

This is a critical reproducibility finding: the INRIA checkpoint must be configured with `resnet50` and `out_keys = ['block4']`. Using `block5` is not compatible, even after removing the DataParallel prefix.

## 8. Repository configuration and preprocessing

The experimentally verified repository configuration is:

```text
backbone: resnet50
pretrained: False
out_keys: ['block4']
in_channel: 3
n_classes: 2
top_k_s: 64
top_k_c: 16
encoder_pos: True
decoder_pos: True
model_pattern: ['X', 'A', 'S', 'C']
```

The inspected repository preprocessing was reproduced as conversion to tensor, resize to 512, then normalization with the INRIA channel statistics:

```text
mean: [0.40672500537632994, 0.42829032416229895, 0.39331840468605667]
std:  [0.029498464618176873, 0.027740088491668233, 0.028246722411879095]
```

The implementation used for HelioScan must preserve this verified checkpoint-compatible configuration and preprocessing unless a separately validated change is documented.

## 9. Hardware validation

Model M was constructed and executed on the target hardware:

- GPU: NVIDIA GeForce RTX 5070 Ti Laptop GPU
- Compute capability: 12.0
- PyTorch: 2.14.0+cu130
- CUDA runtime: 13.0
- `torch.cuda.is_available()`: True

The checkpoint loaded with **0 missing keys and 0 unexpected keys** under the `block4` configuration. CUDA inference completed successfully. Peak GPU memory observed during the isolated 512x512 test was approximately 405 MB.

## 10. Real inference validation

A 512x512 INRIA tile was run through the model:

```text
Input:  (1, 3, 512, 512)
Output: (1, 2, 512, 512)
```

All available 512x512 tiles from `data/test/naip/cedar_park_residential.tif` were also tested. Multiple tiles produced building detections, and the complete-image run produced a plausible building mask after the checkpoint-compatible configuration was established. This TIFF is a local real-image test fixture; it is not evidence that Phase 5 imagery acquisition/integration exists.

These are engineering and inference validations only. No ground-truth comparison was performed for this report, and no IoU, Dice, F1, precision, recall, or other formal accuracy metric is claimed.

## 11. Why Model M was selected

Model M is selected as HelioScan's first frozen baseline because:

- A pretrained building-extraction checkpoint is available.
- Exact checkpoint compatibility was established for `resnet50` with `out_keys = ['block4']`.
- The implementation and checkpoint ran on the target RTX 5070 Ti GPU.
- CUDA inference completed with a two-class, full-resolution 512x512 output.
- Isolated 512x512 GPU memory use was manageable for the tested environment.
- The repository implementation provides a reproducible starting point.
- The baseline permits an inference integration before a custom training pipeline is necessary.

## 12. Alternatives not selected for the first implementation

**Not selected for now** does not mean **rejected permanently**.

- U-Net remains a valid alternative and future training/research path. It was not selected as the first implementation because Model M already has a compatible pretrained checkpoint and has passed engineering inference validation. No claim is made that U-Net performed worse.
- DeepLab-style, SegFormer, and other architectures remain untested alternatives in this record. No comparative result or model-specific reason for rejection is claimed.
- Model M itself may be replaced if evaluation demonstrates a better fit.

## 13. Known limitations

- INRIA training data may bias the model toward its training domain; generalization to other regions is unmeasured.
- Geographic and domain shift outside the evaluated imagery remain open validation risks; the current product scope is US-focused.
- Imagery source, resolution/GSD, season, CRS, band composition, and preprocessing differences can affect results.
- No formal HelioScan ground-truth benchmark has been completed.
- Fine-tuning may be needed after a labeled target-domain evaluation.
- The current evidence establishes checkpoint compatibility and successful inference, not accuracy, optimality, or state-of-the-art performance.
- Model M was not trained by the HelioScan team.

## 14. Decision

**HelioScan Model M is the current frozen baseline for rooftop/building segmentation.** It is selected for the first HelioScan implementation, with its architecture and checkpoint-compatible configuration frozen for reproducibility. Inference integration should be built around this baseline. It is not mathematically optimal, universally best, formally benchmarked as state of the art, guaranteed accurate for every region, or permanently locked against replacement.

## 15. Future model evaluation

Evaluate alternatives or revise the baseline if labeled evaluation shows insufficient segmentation quality, geographic generalization is inadequate, inference speed becomes a bottleneck, memory requirements change, or a better-licensed model becomes available. Compare models using documented datasets and reproducible metrics; do not promote visual plausibility or inference success to an accuracy claim.
