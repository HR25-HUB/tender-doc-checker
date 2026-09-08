# TOF-001.0 Golden Real Tender Dataset

This directory is reserved for the first real tender source snapshot used to certify `TOF-001.0`.

## Rule

Do **not** replace the real tender with synthetic fixture data.

Synthetic files in `tests/test_tof_001_0_source_snapshot.py` validate mechanics only. This golden directory becomes the executable evidence package only after one real tender is selected and frozen.

## Required source metadata

Record before freezing:

- source platform / channel;
- external tender identifier;
- source URL or stable source reference, when available;
- capture timestamp;
- person responsible for selecting the dataset;
- list of all files available at capture time;
- known missing files or access limitations.

## Expected layout after capture

```text
tests/golden/tof_001_0/
├── source/
│   └── <original tender files>
├── manifest.json
└── README.md
```

## PASS gate

`TOF-001.0` is PASS only when:

1. every original tender file available at capture time is represented in `manifest.json`;
2. every captured file has SHA-256;
3. verification succeeds immediately after freeze;
4. a second freeze of unchanged source content produces the same per-file hashes and aggregate `source_hash`;
5. intentional mutation causes verification failure identifying the changed file;
6. no OCR, LLM, Product Identity, pricing, or BID-decision code is invoked.

## Stop condition

Do not start `TOF-001.1 — Immutable TenderSourceSnapshot → Normalized TenderEnvelope` until the real dataset above exists and this gate is green.
