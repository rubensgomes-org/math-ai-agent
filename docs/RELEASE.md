# Release Process

**Currently, only Rubens Gomes is authorized to push a release**

## Prerequisites

1. Ensure the following packages and tools are installed:

    - coreutils package
    - dnsutils package
    - curl 8.7.1 or later
    - gawk 5.4.1 or later
    - gh version 2.97.0 or later (GitHub CLI tool)
    - git version 2.55.0 or later
    - grep version 3.11, 2.6.0-FreeBSD,  or later

2. Ensure a `release` branch is created in the remote Git repository.

3. Ensure the `scripts/test_github.sh` is executed prior to running
   a release to ensure connectivity to GitHub remote repository.

## Environment Variables

The release process is done on a Linux machine using a "Claude Code" custom
slash command `.claude/commands/release-plan.md`. Therefore, it is expected
that a `Claude Code` CLI session is started running on an underlying Linux
`bash` shell with the following environment variables set:

- GIT_AUTHOR_NAME
- GIT_AUTHOR_EMAIL
- GIT_COMMITTER_EMAIL
- GITHUB_USER
- GITHUB_TOKEN
- GH_TOKEN (should be same as GITHUB_TOKEN)

## Starting a Release

- Refer to [.claude/commands/release-plan.md](.claude/commands/release-plan.md) for the list of
  commands that are run during a release.

- The release plan is generated/executed within `Claude Code`. You must start
  `Claude Code`, and run the following custom slash command:

    ```commandline
    cd $(git rev-parse --show-toplevel) || exit
    claude --debug --ide --model opus  --verbose
    # Claude Code edit mode command:
    /release-plan rubensgomes/<proj-name>
    ```

