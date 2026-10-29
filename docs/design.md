# Design

The tool converts various radio schedules into a consistent, validated CSV format for receiver applications, supporting both local use and automated CI exports.

This document describes the requirements, architectural decisions, and trade-offs for the converter. Intended applications are described in [Use cases](use-cases.md). Usage examples live in [README.md](../README.md); the output contract is defined in [format.md](format.md).

## Principles

- **CLI-first and automation-friendly.** Support direct use and unattended batch operations, including CI.
- **One source-independent format.** Produce consistent output across supported sources.
- **Deliberately simplified.** Prioritize common receiver needs over complete representation of every source's semantics. Make the format's limitations explicit.
- **Easy to consume and edit.** Keep the format straightforward for receiver firmware, schedule browsers, and manual editing.
- **Consistent validation.** Provide a validator for generated and hand-edited schedules, and apply the same output rules across conversion, validation, and browsing.
- **Independent consumers.** Let browsers and receivers consume normalized schedules without understanding the original sources.
- **Explicit failure and partial imports.** Reject invalid input by default. Allow partial imports only when explicitly requested, and clearly report omissions.
- **Low maintenance.** Minimize dependencies, special cases, and manually maintained data where practical.
- **Actionable change detection.** Detect unexpected source changes, data anomalies, and lookup-table changes that could affect output correctness. Report issues that require attention while tolerating harmless variation and avoiding routine review overhead.
- **Easy to run independently.** Make it straightforward to run your own instance of the tool and publish its outputs.
- **Preserve meaning and uncertainty.** Retain known restrictions and make uncertainty explicit. Simplification must not silently turn restricted or uncertain broadcasts into definite, unrestricted ones.
- **Compact exports.** Avoid redundant fields and annotations while retaining useful information.
- **Separate source-specific interpretation.** Isolate source differences from shared validation and consumers so each source can evolve independently.
- **Reproducible results and safe updates.** Support offline conversion from retained inputs, make refreshes and partial imports explicit, and preserve previous outputs when conversion fails.

## Implementation details

- Use Python as the primary language and uv for dependency management.
- Use Pydantic for data models and validation.
- Use two validation layers: validate raw source fields before normalization, then validate normalized schedule rows against the output format.
- Decode source files using explicitly defined encodings for each source format; do not guess encodings or silently fall back to alternatives.
- Allow users to select exported columns and filter schedule rows, while preserving required fields and output-format validity.
- Allow users to optionally restrict output to ASCII characters while preserving output-format validity.
- Use Textual for an optional terminal-based schedule browser that reads converted CSV files.
- Let users configure an arbitrary tuning command that the browser invokes through a keyboard shortcut, passing the selected broadcast's frequency to tune a receiver.
- Use GitHub forks as the primary way to run independent instances of the tool.
- Publish schedules primarily as GitHub release assets, with stable names such as `schedules-VARIANT.csv`.
- Let consumers retrieve the latest artifact through `https://github.com/OWNER/REPO/releases/latest/download/schedules-VARIANT.csv`.
- Retain a bounded number of recent releases to prevent storage growth.
- Publish a release only when output data differs from the latest release, or when no release exists yet.
