# Testing And Verification

The current repository uses pytest. Test configuration lives in [pyproject.toml](../../pyproject.toml):

- `pythonpath = ["src"]`
- `testpaths = ["tests"]`

Pytest itself is not currently declared as a project dependency.

## Run The Test Suite

From the repository root, when `pytest` is installed:

```text
python -m pytest
```

FFmpeg-dependent video tests skip when the required FFmpeg tooling is unavailable.

## Current Test Files

- [test_classification.py](../../tests/test_classification.py) - JPEG classification behavior.
- [test_signature_index.py](../../tests/test_signature_index.py) - anywhere signature detection for prefixed MP4 data.
- [test_db.py](../../tests/test_db.py) - run summaries, candidate persistence, and output summaries.
- [test_recovery.py](../../tests/test_recovery.py) - JPEG recovery strategies, candidate generation, color tables, and FFmpeg-gated prefixed MP4 recovery.

Historical legacy source is not part of the pytest suite.

## Documentation And Structured-File Checks

For documentation/index changes:

```text
python -m json.tool docs/agent-index.json
git diff --check
```

No dedicated Markdown formatter or link-checker is configured. Check changed relative links against the tracked repository tree.

## Manual Smoke Test

For a small non-sensitive local sample corpus:

```text
file-uncorrupter scan input --recursive --all-files --db runs.sqlite3
file-uncorrupter recover input output --recursive --all-files --db runs.sqlite3 --save-raw-candidates
file-uncorrupter report --db runs.sqlite3 --output-json report.json --output-csv attempts.csv
```

Verify:

- JSON summaries are printed.
- `runs.sqlite3` is created.
- `.uncorrupter-workspace/configs/` contains a run config snapshot.
- recovered artifacts are written under the chosen output directory.
- `_raw_candidates/` exists only when `--save-raw-candidates` is used.

Keep source evidence separate from every generated path.

## Result Vocabulary

Report checks as one of:

- `passed`
- `failed`
- `blocked`
- `unavailable`
- `not applicable`
- `not run`

Do not report an unavailable or unrun check as passing.
