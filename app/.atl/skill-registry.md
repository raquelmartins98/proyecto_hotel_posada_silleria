# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| review, analyze, check code, /review, static analysis, pre-flight, before dotnet build/run | code-review | C:\Users\raque\.config\opencode\skills\code-review\SKILL.md |
| Go tests, teatest, adding test coverage | go-testing | C:\Users\raque\.config\opencode\skills\go-testing\SKILL.md |
| creating new skill, add agent instructions, document patterns for AI | skill-creator | C:\Users\raque\.config\opencode\skills\skill-creator\SKILL.md |
| creating GitHub issue, reporting bug, requesting feature | issue-creation | C:\Users\raque\.config\opencode\skills\issue-creation\SKILL.md |
| creating pull request, opening PR, preparing changes for review | branch-pr | C:\Users\raque\.config\opencode\skills\branch-pr\SKILL.md |
| judgment day, judgment-day, review adversarial, dual review, doble review, juzgar, que lo juzguen | judgment-day | C:\Users\raque\.config\opencode\skills\judgment-day\SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### code-review
- Use [CRITICAL], [WARNING], [INFO] severity levels for issues
- Critical: null checks, sync-over-async (.Result), missing using/dispose, empty catch blocks
- Check layer separation: no cross-layer references (e.g. UI accessing DAL directly)
- Check async/await patterns: never `.Result` or `.Wait()`, always `await`
- Check resource disposal: I/O, DB, network connections must use `using` / `with`
- Check exception handling: no empty catch blocks, catch specific exception types
- Thread safety: use `Concurrent*` collections for shared state

### go-testing
- Use table-driven tests (slice of test cases with name, input, expected, wantErr)
- Always use `t.Run(name, func(t *testing.T))` for sub-tests
- Use `go-cmp` for diff output on struct comparison failures
- For Bubbletea TUI: use `teatest.NewModel` with `teatest.WithHeadless` for headless mode
- Simulate user input via `tui.SendKey` and `tui.Type` helpers
- Use golden files for complex output comparison
- Test initialization: `t.Helper()` on helper functions, avoid `init()` for test setup

### skill-creator
- Place in `~/.config/opencode/skills/{name}/SKILL.md`
- YAML frontmatter must include: name, description (with Trigger: line), license, metadata (author, version)
- Description MUST include exact trigger text after "Trigger:" — this is how auto-load matching works
- Include compact actionable rules (do X, never Y, prefer Z), NOT purpose/motivation
- For project-specific skills, add a note: "This is a project-level skill for {project}"
- Max 15 lines of compact rules — concise and actionable

### issue-creation
- Blank issues are disabled — MUST use a template (bug report or feature request)
- Every issue gets `status:needs-review` automatically on creation
- A maintainer MUST add `status:approved` before any PR can be opened
- Questions go to Discussions, not issues
- Search existing issues for duplicates before creating new ones
- Fill in ALL required fields and check pre-flight checkboxes before submitting

### branch-pr
- Every PR MUST link an approved issue (must have `status:approved` label)
- Every PR MUST have exactly one `type:*` label
- Branch naming: `^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)\/[a-z0-9._-]+$`
- Use conventional commits: `type(scope): description`
- Run shellcheck on modified scripts before opening PR
- Automated checks must pass before merge is possible
- Blank PRs without issue linkage will be blocked by GitHub Actions

### judgment-day
- Launch TWO independent blind judge sub-agents via `delegate` IN PARALLEL, never sequentially
- Neither judge knows about the other — no cross-contamination
- Verdict synthesis: Confirmed (both found) → fix immediately; Suspect (one found) → needs triage; Contradiction → flag for manual decision
- WARNING classification: real (causes bug in normal use) vs theoretical (requires contrived scenario) → theoretical reported as INFO, not fixed
- After fix → re-launch BOTH judges in parallel (never sequential)
- Max 2 fix iterations before asking user: "Should I continue iterating?"
- Convergence: 0 confirmed CRITICALs + 0 confirmed real WARNINGs = APPROVED
- Before launching judges, resolve skill registry and inject matching compact rules as `## Project Standards (auto-resolved)`

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| AGENTS.md | C:\Users\raque\.config\opencode\AGENTS.md | Global agent instructions — rules, personality, tone, philosophy, expertise, behavior |

Read the convention files listed above for project-specific patterns and rules.
