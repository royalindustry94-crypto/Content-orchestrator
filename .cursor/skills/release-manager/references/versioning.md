# Versioning, tags, changelog

## Version identity

Prefer milestone-aligned tags consistent with existing practice:

| Example | Meaning |
|---------|---------|
| `v0.3.0-milestone-3` | Milestone 3 freeze (see `docs/M3_RELEASE_REPORT.md`) |
| `v0.4.0-milestone-4` | Milestone 4 release candidate / freeze |

If introducing SemVer without milestone suffix, document the scheme in the readiness report and keep it stable thereafter.

## Required release documentation

1. **Version string** — unique; matches intended tag
2. **Tag plan** — annotated tag on the release SHA after readiness VERIFIED (human or authorized process creates the tag; this skill recommends, does not force-push)
3. **Changelog / release notes** — user/operator-visible changes; migrations; breaking changes; known limitations
4. **PR description** — links to design/ADR and specialist reports when applicable

## Changelog minimum sections

```markdown
## [version] — YYYY-MM-DD

### Added
### Changed
### Fixed
### Security
### Migrations
### Known limitations
```

## Checks before recommending tag

- [ ] Tag name matches readiness report version
- [ ] Target SHA == CI/QA/Security SHA
- [ ] Notes list migration head and rollback pointer
- [ ] No secret material in notes
