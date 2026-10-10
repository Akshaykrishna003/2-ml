# PS-23: Code Plagiarism Detector Robust to Obfuscation
## ML and Code-Similarity Engine

This component is responsible for comparing programming submissions and reporting structural and textual similarity evidence.

### Project Structure
- `ps23_engine/core/`: Primary logic for preprocessing, tokenization, AST analysis, and scoring.
- `data/`: Generated synthetic JSONL source corpus.
- `models/`: Reserved for model artifacts; no trained classifier is currently supplied.
- `tests/`: Regression, unit, and safe robustness tests.
- `benchmarks/`: Dataset preparation, fixed-holdout evaluation, and performance benchmark scripts.
- `reports/`: Machine-generated evaluation and performance results.

### Setup
Use Python 3.13 on Windows (the included Python 3.8 installation is 32-bit and cannot install current scikit-learn/SciPy wheels).

```powershell
py -3.13 -m pip install -r requirements.txt
py -3.13 -m pytest -q
py -3.13 -m benchmarks.prepare_dataset
py -3.13 -m benchmarks.evaluate
py -3.13 -m benchmarks.benchmark
```

Optional output paths and benchmark sizes:

```powershell
py -3.13 -m benchmarks.prepare_dataset --output data\synthetic_programs.jsonl
py -3.13 -m benchmarks.evaluate --output reports\evaluation.json
py -3.13 -m benchmarks.benchmark --sizes 100 500 1000 --output reports\performance.json
```

The corpus is hand-authored synthetic material. `family_id` links every original and controlled variant; the evaluator splits by task group so variants cannot leak across train, validation, and test. Evaluation reports token-only, AST-only, and combined fixed-threshold baselines, transformation breakdowns, and confusion matrices. A trained model is not provided; no classifier metrics are claimed.

### Validation Results

See [reports/evaluation.json](reports/evaluation.json) and [reports/performance.json](reports/performance.json) for raw measurements. The measured 1,000-file synthetic all-pairs run completed in 97.67 seconds on an Intel Core i7-1065G7 with Python 3.13.3. This meets the stated 10-minute timing target only for this fixture and configuration; it is not a deployment guarantee.

Security checks and unresolved limitations are recorded in [reports/security_findings.md](reports/security_findings.md).

### Design Principles
- **Neutrality:** Reports similarity evidence, not plagiarism verdicts.
- **Reproducibility:** Fixed seeds and documented hyperparameters.
- **Explainability:** Every score is backed by extracted structural or textual evidence.
- **Efficiency:** A synthetic 1,000-file all-pairs timing is recorded; real-workload performance still requires measurement.
