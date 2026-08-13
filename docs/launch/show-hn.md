# Submission title

Show HN: Ailumetra – Reproducible local benchmarks for multimodal models

# Submission URL

<https://github.com/AlbertXXuu/OpenMultimodalLab>

# First-comment draft

I built this after finding that local VLM comparisons often preserve the final
answer but not enough execution evidence to reproduce the trade-off.

OpenMultimodalLab treats raw task-level JSONL and a SHA-bound environment/run
manifest as the source of truth. The report is generated later and can be
rebuilt without rerunning the model. Runs flush each record durably, failures
remain in the dataset, and strict resume rejects a prefix that does not match
the current protocol.

The first release compares two pinned small VLMs on the same 102-task grid and
8 GB laptop GPU, with one warm-up and three measured repetitions. The scope is
intentionally narrow: controlled synthetic media, one hardware profile, and
two models. I am sharing the raw results and the limitations rather than
claiming a general model ranking.

The question I would most value feedback on is whether the artifact contract
is sufficient for someone else to audit or extend the comparison. Independent
clean-environment run reports are especially useful.

# Launch gate

Use this draft only after at least one non-author has completed the quick start
or after verified first-run blockers have been fixed. Show HN should test the
project's broader relevance, not serve as the first installation test.
