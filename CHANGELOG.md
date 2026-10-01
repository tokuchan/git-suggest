# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [CalVer](https://calver.org/) (`YY.MM.patch`), not semver.

## [Unreleased]

### Added
- **CHANGELOG.md**:
    Added a new CHANGELOG.md starting with an Unreleased section and an
    initial 26.09.0 release entry.
- **src/git_suggest/changelog.py**:
    Added a changelog module that splits, merges, and renders entries
    into CHANGELOG.md's Unreleased section and commits the result.
- **src/git_suggest/release.py**:
    Added a release module that stamps Unreleased as a dated release,
    rewrites footer compare links, and commits the change.
- **src/git_suggest/scan_ref.py**:
    Added a scan_ref module that translates a ref or range into git diff
    arguments and builds a scan report from them.
- **docs/adr/0022-changelog-file-and-changelog-subcommand.md**:
    Added ADR 0022 documenting the CHANGELOG.md format and the changelog
    subcommand's design.
- **docs/adr/0023-release-subcommand-tag-aware-compare-links.md**:
    Added ADR 0023 documenting the release subcommand's tag-aware
    compare link resolution.
- **docs/adr/0024-scan-ref-subcommand.md**:
    Added ADR 0024 documenting the scan-ref subcommand's refspec
    handling.
- **src/git_suggest/cli.py**:
    Added scan-ref, changelog, and release CLI commands.
- **src/git_suggest/config.py**:
    Added changelog_commit_message_template and
    release_commit_message_template config fields.
- **src/git_suggest/version.py**:
    Added tag_name_for_version, find_tag_for_version,
    find_commit_for_version, and resolve_version_endpoint helpers.
- **tests/test_changelog.py**:
    Added tests covering splitting, parsing, merging, and appending
    changelog sections.
- **tests/test_release.py**:
    Added tests covering stamping Unreleased as a release and rewriting
    compare links.
- **tests/test_scan_ref.py**:
    Added tests covering refspec range detection and ref-based scan
    report building.

### Changed
- **CONTEXT.md**:
    Added glossary entries for Changelog file, Unreleased section,
    Release, Compare link, and Ref scan, and listed the new subcommands.
- **README.md**:
    Documented the new CHANGELOG.md, the changelog and release workflow,
    and renamed config template fields.
- **src/git_suggest/scan.py**:
    Refactored staged-diff-specific functions to take a diff_args
    parameter and extracted a shared build_report function reused by
    scan-ref.
- **tests/test_scan.py**:
    Updated tests to call the renamed diff_files function with explicit
    diff args.
- **tests/test_cli.py**:
    Added tests for the scan-ref, changelog, and release CLI commands.
- **tests/test_config.py**:
    Renamed the bump commit message template test to match the renamed
    config field.
- **tests/test_version.py**:
    Updated tests for the renamed bump_commit_message_template field and
    added tests for the new tag/commit endpoint resolution helpers.

## [26.09.0] - 2026-09-30

Initial CalVer release.
