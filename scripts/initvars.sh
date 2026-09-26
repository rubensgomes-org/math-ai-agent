#!/usr/bin/env bash
## SPDX-License-Identifier: MIT
##
## Resets this repository's GitHub Actions secrets to the values
## held by the current shell environment.
##
## Requirements:
##  1) Bash functions libraries installed at "${HOME}/lib/sh-lib".
##  2) GNU bash version 4.2 or higher, required by associative
##     arrays.
##  3) GitHub CLI (gh) 2.99 or higher, authenticated.
##  4) getopt from util-linux 2.30.2 or higher.
##
## Author: Rubens Gomes
## NOTE:   Initial implementation was generated with AI assistance
##         and subsequently reviewed and approved by the author.
##
## This project's source code and documentation were generated with
## the assistance of Artificial Intelligence (AI). For more
## information, please refer to the `AI_DISCLAIMER.md` document
## located in the project's root directory.


#####################################################################
## Early bash version guard. The managed-entry maps below need
## associative arrays (bash 4+). macOS ships 3.2 as /bin/bash, which
## fails "declare -A" with a misleading error, so this fails first
## with an actionable one. sh::init() (see main()) re-checks the
## fuller 4.2 requirement once strict mode is active.
#####################################################################
if (( BASH_VERSINFO[0] < 4 )); then
  printf "ERROR: bash 4+ required; running %s.\n" \
    "${BASH_VERSION}" >&2
  printf "       On macOS: brew install bash\n" >&2
  exit 1
fi


#####################################################################
## GLOBAL CONSTANTS #################################################

# shell script program name
declare PRG
PRG="$(
  basename -- "${0}" || {
    printf "failed to determine the program basename." >&2
    exit 1
  }
)"

# minimum Bash major / minor version required
# shellcheck disable=SC2034
readonly BASH_MAJOR_VERSION="4"
# shellcheck disable=SC2034
readonly BASH_MINOR_VERSION="2"

# Set to TRUE when debugging code using bassupport-pro. This is
# required to bypass trap handlers which crashes code when running
# from debugger
readonly IS_DEBUGGER=FALSE

# extra tools required by this script to run.
[[ ! -v REQUIRED_TOOLS ]] && readonly -a REQUIRED_TOOLS=(
  "gh"
  "getopt"
)

#####################################################################
## INCLUDES #########################################################

[[ -d "${HOME}/lib/sh-lib" ]] || {
  printf "missing %s\n" "${HOME}/lib/sh-lib" >&2
  exit 1
}

# logging message library
# shellcheck source=/dev/null
source "${HOME}/lib/sh-lib/msg_lib.sh" || exit

# operating system library
# shellcheck source=/dev/null
source "${HOME}/lib/sh-lib/os_lib.sh" || exit

# bash library
# shellcheck source=/dev/null
source "${HOME}/lib/sh-lib/sh_lib.sh" || exit


#####################################################################
## MANAGED GITHUB ACTIONS SECRETS ####################################
##
## Keys are Actions secret names exactly as they appear in the
## repository settings. Values are resolved from the shell
## environment. Secret values are never printed or
## logged -- see print_planned_secrets() and create_action_secrets().
##
## Bash does not preserve associative-array order, so
## ACTION_SECRET_ORDER fixes a presentation order.
#####################################################################
declare -Ar ACTION_SECRETS=(
  [PYPI_API_TOKEN]="${PYPI_API_TOKEN:-}"
  [SONAR_TOKEN]="${SONAR_TOKEN:-}"
)

declare -ar ACTION_SECRET_ORDER=(
  PYPI_API_TOKEN
  SONAR_TOKEN
)

# Secrets this script used to manage and no longer does. The delete
# phase sweeps these too; the create phase ignores them.
declare -ar RETIRED_ACTION_SECRETS=()

declare -Ar REQUIRED_SECRET_SOURCES=(
  [PYPI_API_TOKEN]="PYPI_API_TOKEN"
  [SONAR_TOKEN]="SONAR_TOKEN"
)


#####################################################################
## GLOBAL VARIABLES #################################################

# Boolean flag: print the plan and stop, changing nothing.
declare g_is_dry_run=FALSE

# Boolean flag: delete managed secrets, do not recreate them.
declare g_is_delete_only=FALSE


#####################################################################
## FUNCTIONS #########################################################

#####################################################################
## Prints help to stdout.
## Globals:
##  PRG
## Arguments:
##  None.
## Returns:
##   0 always.
#####################################################################
help() {
  cat <<EOF

"${PRG}" resets this repository's GitHub Actions secrets to the
values held by the current shell environment.

Usage:
  ${PRG} [options]

General Non Argument Options:

  -d, --debug          prints debug messages
  -h, --help           prints this help
  -n, --dry-run        prints the plan only, changes nothing
  -o, --delete-only    deletes secrets, does not recreate them
  -q, --quiet          prints only error|fatal messages
  -v, --verbose        adds extra details to messages
  -x, --trace           traces commands

By default, every managed Actions secret is deleted and recreated
from the current shell environment. Pass -o/--delete-only to delete
them without recreating them.
EOF
}

#####################################################################
## Prints usage to stderr.
## Globals:
##  PRG
## Arguments:
##  None.
## Returns:
##   2 always.
#####################################################################
usage() {
  cat <<EOF
Usage:  ${PRG} [options]
More information with: "${PRG} -h"
EOF

  return 2
} >&2

#####################################################################
## Resets global variables to their initial state.
## Globals:
##  g_is_delete_only
##  g_is_dry_run
## Arguments:
##  None.
## Returns:
##   0 always.
#####################################################################
reset_globals() {
  g_is_dry_run=FALSE
  g_is_delete_only=FALSE
}

#####################################################################
## Parses user's command line input option arguments.
## Globals:
##  g_is_delete_only
##  g_is_dry_run
## Arguments:
##  Bash shell CLI input arguments.
## Returns:
##   0 if okay; 2 on a bad argument.
#####################################################################
parse_options() {
  reset_globals

  local temp

  if ! temp=$(
    getopt \
      --o 'dhnoqvx' \
      --long \
        'debug,delete-only,dry-run,help,quiet,trace,verbose' \
      --name "${PRG}" \
      -- "${@}"
  ); then
    msg::error "failed to parse CLI input arguments.\n"
    usage
    return 2
  fi

  eval set -- "${temp}"
  local quiet=FALSE

  while true; do

    case "${1}" in

      ########## --debug ############################################
      '-d' | '--debug')
        if [[ "${quiet}" == TRUE ]]; then
          msg::warn "-q overrides -d; debug stays disabled.\n"
        else
          msg::enable_debug
        fi
        shift
        continue
        ;;

      ########## --help #############################################
      '-h' | '--help')
        help
        exit 0
        ;;

      ########## --dry-run ##########################################
      '-n' | '--dry-run')
        g_is_dry_run=TRUE
        shift
        continue
        ;;

      ########## --delete-only ######################################
      '-o' | '--delete-only')
        g_is_delete_only=TRUE
        shift
        continue
        ;;

      ########## --quiet ############################################
      '-q' | '--quiet')
        quiet=TRUE
        msg::enable_quiet
        shift
        continue
        ;;

      ########## --verbose ##########################################
      '-v' | '--verbose')
        msg::enable_verbose
        shift
        continue
        ;;

      ########## --trace ############################################
      '-x' | '--trace')
        msg::enable_tracing
        shift
        continue
        ;;

      ########## -- #################################################
      '--')
        shift
        break
        ;;

      ########## * ##################################################
      *)
        msg::arg_error "invalid option [%s].\n" "${1}"
        usage
        return 2
        ;;

    esac
  done

  msg::debug "%s completed successfully.\n" "${FUNCNAME[0]}"
}

#####################################################################
## Checks that every tool in REQUIRED_TOOLS is installed.
## Globals:
##  REQUIRED_TOOLS
## Arguments:
##  None.
## Returns:
##   0 if okay; 127 if a tool is missing.
#####################################################################
check_required_tool() {
  local tool

  for tool in "${REQUIRED_TOOLS[@]}"; do

    if ! os::is_installed "${tool}"; then
      msg::warn "Missing a required tool [%s].\n" "${tool}"
      return 127
    fi

  done
}

#####################################################################
## Verifies gh is authenticated. Installation itself was already
## checked by check_required_tool().
## Arguments:
##  None.
## Returns:
##   0 when authenticated; 1 otherwise.
#####################################################################
require_github_auth() {
  msg::debug "checking gh authentication.\n"

  if ! gh auth status > /dev/null 2>&1; then
    msg::error "gh is not authenticated.\n"
    msg::error "Run: gh auth login\n"
    return 1
  fi
}

#####################################################################
## Resolves the repository every gh call targets. Prefers GH_REPO
## (which gh itself honours), then asks gh to read the git remote.
## Arguments:
##  None.
## Outputs:
##  stdout: the resolved "OWNER/REPO".
## Returns:
##   0 on success; 1 when no repository can be determined.
#####################################################################
resolve_repository() {
  local repo

  if [[ -n "${GH_REPO:-}" ]]; then
    printf "%s" "${GH_REPO}"
    return 0
  fi

  if ! repo="$(
    gh repo view --json nameWithOwner --jq '.nameWithOwner' \
      2> /dev/null
  )" || [[ -z "${repo}" ]]; then
    msg::error "could not determine the target repository.\n"
    msg::error \
      "Run inside the clone, or export GH_REPO=OWNER/REPO.\n"
    return 1
  fi

  printf "%s" "${repo}"
}

#####################################################################
## Fails if any managed Actions secret resolved to an empty value.
## Globals:
##  ACTION_SECRETS
##  ACTION_SECRET_ORDER
##  REQUIRED_SECRET_SOURCES
## Arguments:
##  None.
## Returns:
##   0 when every value is set; 1 otherwise.
#####################################################################
validate_secret_values() {
  local -a missing=()
  local name

  for name in "${ACTION_SECRET_ORDER[@]}"; do
    [[ -z "${ACTION_SECRETS[${name}]}" ]] && missing+=("${name}")
  done

  (( ${#missing[@]} == 0 )) && return 0

  msg::error "%d secret(s) have no value.\n" "${#missing[@]}"
  for name in "${missing[@]}"; do
    msg::error "  %-38s <- %s\n" "${name}" \
      "${REQUIRED_SECRET_SOURCES[${name}]:-${name}}"
  done

  return 1
}

#####################################################################
## Prints the gh/git environment this run will act under.
## Arguments:
##  1: target repository ("OWNER/REPO").
## Outputs:
##  Writes the environment block to stdout.
## Returns:
##   0 always.
#####################################################################
print_gh_environment() {
  local -r repo="${1:?repo is required}"
  local -ar names=(
    GH_HOST
    GH_REPO
    GITHUB_USER
    GIT_AUTHOR_EMAIL
    GIT_COMMITTER_EMAIL
    GIT_AUTHOR_NAME
  )
  local name

  printf "GitHub environment\n"
  printf "%s\n" "------------------"

  for name in "${names[@]}"; do
    printf "  %-20s %s\n" "${name}" "${!name:-<unset>}"
  done

  printf "  %-20s %s\n" "target repository" "${repo}"
  printf "\n"
}

#####################################################################
## Prints the Actions secrets this run will change. Values are
## never shown.
## Globals:
##  ACTION_SECRET_ORDER
## Arguments:
##  1: TRUE when running delete-only, FALSE otherwise.
## Outputs:
##  Writes the secret name table to stdout.
## Returns:
##   0 always.
#####################################################################
print_planned_secrets() {
  local -r is_delete_only="${1:?is_delete_only is required}"
  local action="delete and recreate"
  local name

  [[ "${is_delete_only}" == TRUE ]] && action="delete"

  printf "Actions secrets to %s (%d):\n" \
    "${action}" "${#ACTION_SECRET_ORDER[@]}"

  for name in "${ACTION_SECRET_ORDER[@]}"; do
    printf "  %-38s (value hidden)\n" "${name}"
  done

  printf "\n"
}

#####################################################################
## Prompts for confirmation before any Actions secret is changed.
## Arguments:
##  1: target repository ("OWNER/REPO").
##  2: TRUE when running delete-only, FALSE otherwise.
## Returns:
##   0 when confirmed; 1 when declined.
#####################################################################
confirm_changes() {
  local -r repo="${1:?repo is required}"
  local -r is_delete_only="${2:?is_delete_only is required}"
  local action="Delete and recreate"

  [[ "${is_delete_only}" == TRUE ]] && action="Delete"

  printf "%s these Actions secrets on %s?\n" \
    "${action}" "${repo}" >&2

  msg::yes_no
}

#####################################################################
## Lists the names that currently exist remotely for a kind.
## Arguments:
##  1: kind, "variable" or "secret".
##  2: target repository ("OWNER/REPO").
## Outputs:
##  stdout: one name per line.
## Returns:
##   0 on success; 1 if the listing fails.
#####################################################################
list_remote_names() {
  local -r kind="${1:?kind is required}"
  local -r repo="${2:?repo is required}"

  if ! gh "${kind}" list --repo "${repo}" \
      --json name --jq '.[].name' 2> /dev/null; then
    msg::error "could not list Actions %ss on %s.\n" \
      "${kind}" "${repo}"
    msg::error "Check that the token has the repo admin scope.\n"
    return 1
  fi
}

#####################################################################
## Deletes a single Actions variable or secret.
## Arguments:
##  1: kind, "variable" or "secret".
##  2: name to delete.
##  3: target repository ("OWNER/REPO").
## Returns:
##   0 on success; 1 if the delete fails.
#####################################################################
gh_delete_one() {
  local -r kind="${1:?kind is required}"
  local -r name="${2:?name is required}"
  local -r repo="${3:?repo is required}"

  if ! gh "${kind}" delete "${name}" --repo "${repo}" \
      > /dev/null 2>&1; then
    msg::error "failed to delete %s %s on %s.\n" \
      "${kind}" "${name}" "${repo}"
    return 1
  fi
}

#####################################################################
## Creates (upserts) a single Actions variable or secret.
## Arguments:
##  1: kind, "variable" or "secret".
##  2: name to create.
##  3: value to set.
##  4: target repository ("OWNER/REPO").
## Returns:
##   0 on success; 1 if the create fails.
#####################################################################
gh_create_one() {
  local -r kind="${1:?kind is required}"
  local -r name="${2:?name is required}"
  local -r value="${3:?value is required}"
  local -r repo="${4:?repo is required}"

  if ! gh "${kind}" set "${name}" --repo "${repo}" \
      --body "${value}" > /dev/null 2>&1; then
    msg::error "failed to set %s %s on %s.\n" \
      "${kind}" "${name}" "${repo}"
    return 1
  fi
}

#####################################################################
## Deletes every managed secret that currently exists remotely,
## plus any RETIRED_ACTION_SECRETS. Only names present remotely are
## deleted -- a partially-populated repository is the normal case.
## Globals:
##  ACTION_SECRET_ORDER
##  RETIRED_ACTION_SECRETS
## Arguments:
##  1: target repository ("OWNER/REPO").
## Outputs:
##  Writes progress to stdout.
## Returns:
##   0 on success; 1 on the first failed delete.
#####################################################################
delete_action_secrets() {
  local -r repo="${1:?repo is required}"
  local remote
  local name

  remote="$(list_remote_names "secret" "${repo}")" || return 1

  printf "Deleting Actions secrets...\n"

  for name in "${ACTION_SECRET_ORDER[@]}" \
      "${RETIRED_ACTION_SECRETS[@]}"; do

    if ! grep -Fxq "${name}" <<< "${remote}"; then
      msg::debug "  skip   %s (not present)\n" "${name}"
      continue
    fi

    msg::debug "  delete %s\n" "${name}"
    gh_delete_one "secret" "${name}" "${repo}" || return 1

  done
}

#####################################################################
## Creates every managed secret from ACTION_SECRETS. gh's "set" is
## an upsert, so this also repairs a run interrupted between the
## delete and create phases. The value is never logged.
## Globals:
##  ACTION_SECRETS
##  ACTION_SECRET_ORDER
## Arguments:
##  1: target repository ("OWNER/REPO").
## Outputs:
##  Writes progress to stdout.
## Returns:
##   0 on success; 1 on the first failed create.
#####################################################################
create_action_secrets() {
  local -r repo="${1:?repo is required}"
  local name
  local value

  printf "Creating Actions secrets...\n"

  for name in "${ACTION_SECRET_ORDER[@]}"; do
    value="${ACTION_SECRETS[${name}]}"
    msg::debug "  create %s\n" "${name}"
    gh_create_one "secret" "${name}" "${value}" "${repo}" \
      || return 1
  done
}

#####################################################################
## Catches and handles signals defined in the "trap" command.
## Globals:
##  FUNCNAME
## Arguments:
##  1: signal name, as passed by sh::curry_trap_command.
## Exits:
##   An exit status code based on the signal being handled.
#####################################################################
signal_handler() {
  local -r rc=$?
  local -r signal="${1:-}"
  local exit_code="${rc}"

  trap - ERR EXIT HUP INT QUIT TERM

  case "${signal}" in
    HUP)
      msg::warn "controlling terminal hung up: SIGHUP\n"
      exit_code=129 # 1+128
      ;;
    INT)
      msg::warn "interrupted by the user (control-c): SIGINT\n"
      exit_code=130 # 2+128
      ;;
    QUIT)
      msg::warn "interrupted by an unexpected event: SIGQUIT\n"
      exit_code=131 # 3+128
      ;;
    TERM)
      msg::warn "asked to stop: SIGTERM\n"
      exit_code=143 # 15+128
      ;;
    ERR)
      msg::warn "interrupted by a Bash ERR trap.\n"
      ;;
    EXIT) ;;
    *)
      msg::warn "unexpected signal: %s\n" "${signal}"
      ;;
  esac

  exit "${exit_code}"
}

#####################################################################
## Entry point.
## Globals:
##  IS_DEBUGGER
##  PRG
##  g_is_delete_only
##  g_is_dry_run
## Arguments:
##  The script's own "$@".
## Returns:
##   0 on success; non-zero otherwise.
#####################################################################
main() {
  reset_globals

  check_required_tool || return

  parse_options "$@" || return

  msg::debug "Bash version: %s\n" "${BASH_VERSION}"
  msg::info "Running %s\n" "${PRG}"

  if [[ "${IS_DEBUGGER}" != TRUE ]]; then
    sh::init || return
    local -ar signals=("ERR" "HUP" "INT" "TERM" "QUIT" "EXIT")
    sh::curry_trap_command "signal_handler" "${signals[*]}" \
      || return
  fi

  require_github_auth || return

  local repo
  repo="$(resolve_repository)" || return

  if [[ "${g_is_delete_only}" != TRUE ]]; then
    validate_secret_values || return
  fi

  print_gh_environment "${repo}"
  print_planned_secrets "${g_is_delete_only}"

  if [[ "${g_is_dry_run}" == TRUE ]]; then
    msg::info "Dry run: no changes made.\n"
    return 0
  fi

  if ! confirm_changes "${repo}" "${g_is_delete_only}"; then
    msg::info "Declined. Nothing was changed.\n"
    exit 0
  fi

  delete_action_secrets "${repo}" || return

  if [[ "${g_is_delete_only}" != TRUE ]]; then
    create_action_secrets "${repo}" || return
  fi

  msg::info "Done on %s.\n" "${repo}"
}

#####################################################################
## ------------------------------------------------------------------
## -------------------- >>> Main Program Body <<< -------------------
## ------------------------------------------------------------------

if ! main "$@"; then
  printf "\n%s failed!\n" "${PRG}" >&2
  exit 1
fi
