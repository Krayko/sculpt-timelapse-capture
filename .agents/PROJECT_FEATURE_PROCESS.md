# Project Feature Process

These instructions define how agents should handle feedback, clarification, code changes, branches, merges, and pushes for this repository.

## Prompt Modes

If the user's prompt starts with `provide feedback` or `clarify`, treat the request as read-only.

For read-only prompts:

- Do not edit files.
- Do not create commits.
- Do not create branches unless the user explicitly asks for repository setup.
- Do not run formatting or build commands that modify files.
- Provide analysis, recommendations, or explanations only.

This rule is case-insensitive and applies to prompts that begin with those words, such as `Provide feedback:` or `Clarify the following:`.

## Feature Branch Workflow

For any requested code, documentation, packaging, or repository change:

1. Check the current branch and working tree status.
2. Create or switch to a relevant feature branch before making changes.
3. Use a branch name that describes the work, such as `feature/session-metadata` or `fix/timer-event-handling`.
4. Keep changes scoped to the requested feature or fix.
5. Validate the change with the relevant local checks.
6. Commit the feature branch when the change is complete.
7. Summarize the branch, commit, files changed, and validation results.

## Merge Approval

Do not merge a feature branch into `main` without explicit user approval.

When the feature branch is ready, ask for approval before merging and include:

- Branch name
- Commit hash
- Summary of changes
- Validation performed
- Any known risks or untested behavior

## Push Approval

Do not push `main` to GitHub without explicit user approval.

This includes:

- `git push`
- `git push origin main`
- GitHub CLI commands that push `main`
- Release work that requires pushing new commits or tags from `main`

Feature branches may also require approval before pushing if the user has not asked to publish them.

## Release Approval

Do not create or update a GitHub Release without explicit user approval.

Before release creation, confirm:

- Version number
- Release notes
- Attached package zip
- Whether the release should be latest, prerelease, or draft
