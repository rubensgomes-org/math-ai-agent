---
description: Generate a release plan for the project.
argument-hint: Git repository name (e.g., rubensgomes-org/math-ai-agent)
---

# Generate Release Plan

1. If no argument is provided, respond with "Error: Git repository name is
   required." and stop.
2. If the argument is provided, check if the $ARGUMENT repository exists.
3. MUST run `scripts/test_github.sh $ARGUMENT`, and ensure it succeeds;
   otherwise, it MUST report error and stop.
4. MUST update the project documentation files to ensure it is up-to-date with
   the recent code changes
5. Now, you MUST create a NEW release plan containing following steps:
    - MUST run `poetry run mypy src/` and fix any issues.
    - MUST run `poetry run isort src/ tests/` and fix any issues.
    - MUST run `poetry run black src/ tests/` and fix any issues.
    - MUST run `poetry run pytest` and fix any issues.
    - MUST run `export SOURCE_DATE_EPOCH=$(date +%s); poetry build -v` and fix
      any issues.
    - MUST ensure a `CHANGELOG.md` file exists in the project root folder.
    - MUST update the `CHANGELOG.md` with the current release changes.
    - MUST commit all changes to main, create a new version tag, push, and
      create a GitHub release
6. MUST save the release plan in the project's docs folder
7. MUST mark off checkboxes as steps in the plan are completed

