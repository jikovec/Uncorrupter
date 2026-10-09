# Benchmark Ground Truth

`file-uncorrupter benchmark` uses the same bounded recovery path as `recover`. Its optional `--ground-truth` file supplies labels needed for classification accuracy, recovery accuracy, fidelity accuracy, false-positive rate, and false-negative rate. Metrics that cannot be derived from supplied labels remain unavailable; the CLI does not infer ground truth from its own output.

## Command

```powershell
file-uncorrupter benchmark .\corpus .\benchmark-output `
  --recursive --all-files `
  --goal repair --goal extract --goal preview `
  --ground-truth .\corpus-ground-truth.json `
  --db .\benchmark.sqlite3 `
  --manifest .\benchmark-manifest.json
```

Keep the label file outside the input root. Otherwise it becomes an observed corpus file and will be reported as an unexpected extra unless it is labeled too.

## Schema Version 1

```json
{
  "schema_version": 1,
  "dataset_name": "synthetic-smoke-v1",
  "files": {
    "documents/example.docx": {
      "family": "docx",
      "recoverable": true,
      "acceptable_grades": ["validated_original", "partial_content"],
      "source_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    },
    "negative/random.bin": {
      "family": "unknown",
      "recoverable": false,
      "acceptable_grades": []
    },
    "media/preview-only.mp4": {
      "family": "mp4",
      "recoverable": true,
      "acceptable_grades": ["preview_only"]
    }
  }
}
```

Top-level fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `schema_version` | Yes | Must be integer `1`. |
| `dataset_name` | No | Human label, truncated to 200 characters; the JSON filename stem is used when omitted. |
| `files` | Yes | Object mapping safe relative corpus paths to expectation objects. |

Per-file fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `family` | Conditional | Expected classification family or label. A non-empty string when present. |
| `recoverable` | Conditional | `true` expects a successful recovery claim; `false` is a negative sample; `null`/omission does not score recoverability. |
| `acceptable_grades` | Conditional | Any listed outcome grade is acceptable for fidelity scoring. An empty or omitted list does not score fidelity. |
| `source_sha256` | No | Optional 64-character hexadecimal identity pin. Mismatches are reported and excluded from correct-count credit. |

At least one of `family`, `recoverable`, or non-empty `acceptable_grades` is required for each file.

Valid grades are:

- `validated_original`
- `validated_normalized`
- `partial_content`
- `preview_only`
- `unavailable_dependency`
- `budget_exceeded`
- `cancelled`
- `failed`

## Validation And Safety

The loader:

- requires UTF-8 JSON and rejects invalid JSON;
- limits the label file to 16 MiB and 100,000 file entries;
- normalizes every key as a contained relative path and rejects absolute/traversal paths;
- rejects duplicate paths after case-insensitive normalization;
- validates field types, grades, and SHA-256 syntax;
- records the label filename and SHA-256 in benchmark evidence.

The ground-truth file contains labels, not recovered payloads. Do not place secrets, customer data, source excerpts, passwords, or private keys in it.

## Metric Semantics

Classification accuracy:

```text
classification_correct / classification_labeled
```

A match accepts either the observed classification family or label. A pinned source hash must also match for the result to receive correct-count credit.

Recovery accuracy:

```text
recovery_correct / recoverability_labeled
```

A recovery claim exists when the run records a successful output, a recovered/partial file status, or one of the successful grades: `validated_original`, `validated_normalized`, `partial_content`, or `preview_only`.

False-positive rate:

```text
false_positives / negative_samples
```

A false positive is an explicit `recoverable: false` sample for which the run nevertheless makes a recovery claim.

False-negative rate:

```text
false_negatives / positive_samples
```

A false negative is an explicit `recoverable: true` sample for which the run makes no recovery claim.

Fidelity accuracy:

```text
fidelity_correct / fidelity_labeled
```

A file passes when at least one observed attempt grade is in `acceptable_grades`. This is a policy label, not a byte-level comparison. A release-quality corpus should also verify expected artifact hashes or semantic content through external corpus tooling.

The same counters/rates are emitted globally and per expected `family` group. Missing labeled files, extra observed files, and source-identity mismatches are listed separately.

## Memory Measurement Boundary

During the recovery phase, the benchmark samples the main Python process resident set size (RSS):

- Windows: process working set;
- Linux with `/proc`: resident pages from `/proc/self/statm`;
- compatible fallback platforms: `resource.getrusage`.

Evidence includes sampling method, interval, number of samples, baseline, peak, peak-over-baseline, and any sampling error. `children_included` is explicitly `false`: FFmpeg, qpdf, 7-Zip, LibreOffice, isolation wrappers, and other child-process memory are not part of this metric. Treat it as main-process pressure, not total job memory.

## Building A Defensible Corpus

For each format/variant, include:

1. valid positive samples;
2. repairable truncation/index/checksum damage;
3. deliberately unrecoverable negatives;
4. wrong suffix and misleading embedded-signature cases;
5. encrypted, active-content, path-attack, and resource-limit cases where applicable;
6. expected family, recoverability, acceptable grade, and source hash;
7. separately maintained expected artifact/content hashes for successful cases;
8. license and provenance metadata outside private user data.

Run the corpus at least twice with the same version, exact source commit, platform, Python, configuration, and tool identities. Compare normalized manifest ordering and artifact hashes, report per-format sample counts, and never turn a small synthetic fixture rate into a general product recovery claim.
