#!/bin/bash
################################################################################
# GitHub Connectivity Test Script
#
# Purpose:
#   Tests multiple connectivity methods to a GitHub repository to verify
#   network access, API availability, and authentication status.
#
# Usage:
#   test_github.sh <owner/repo>
#
# Example:
#   test_github.sh rubensgomes/javamcp
#
# Exit Codes:
#   0 - All critical tests passed
#   1 - One or more tests failed or missing dependencies
#
# Author: Generated with Claude Code
################################################################################

set -e

################################################################################
# Global Variables
################################################################################

# Repository information (set from command line argument)
REPO=""
GITHUB_URL=""
GITHUB_API_URL=""

# Test counters
declare -i PASSED=0
declare -i FAILED=0

# Color codes for output formatting
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

################################################################################
# Helper Functions
################################################################################

#
# Prints usage information and exits
#
# Arguments:
#   None
# Returns:
#   Exits with code 1
#
usage() {
    echo "Error: Repository name is required"
    echo "Usage: $0 <owner/repo>"
    echo "Example: $0 rubensgomes/javamcp"
    exit 1
}

#
# Validates repository name format (owner/repo)
#
# Arguments:
#   $1 - Repository name to validate
# Returns:
#   0 if valid format, 1 if invalid
#
validate_repo_format() {
    local repo="$1"

    if ! echo "${repo}" | grep -qE '^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$'; then
        echo -e "${RED}Error:${NC} Invalid repository format"
        echo "Usage: $0 <owner/repo>"
        echo "Example: $0 rubensgomes/javamcp"
        return 1
    fi

    return 0
}

#
# Checks if a command exists in the system
#
# Arguments:
#   $1 - Command name to check
# Returns:
#   0 if command exists, 1 if not found
#
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

#
# Checks for required and optional dependencies
#
# Arguments:
#   None
# Returns:
#   0 if all required dependencies found, 1 if missing required dependencies
# Side Effects:
#   Prints dependency check results to stdout
#
check_dependencies() {
    echo "Checking required dependencies..."

    local -a missing_deps=()
    local -a optional_deps=()

    # Check for critical dependencies (required for core tests)
    local -a required_commands=("curl" "git" "host" "timeout" "grep" "awk")

    for cmd in "${required_commands[@]}"; do
        if ! command_exists "$cmd"; then
            missing_deps+=("$cmd")
        fi
    done

    # Report missing required dependencies
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${RED}Error: Missing required dependencies${NC}"
        echo ""
        echo "The following commands are required but not found:"
        for dep in "${missing_deps[@]}"; do
            echo -e "  ${RED}✗${NC} $dep"
        done
        echo ""
        echo "Please install missing dependencies:"
        echo "  Ubuntu/Debian: sudo apt-get install curl git dnsutils coreutils grep gawk"
        echo "  RHEL/CentOS:   sudo yum install curl git bind-utils coreutils grep gawk"
        echo ""
        return 1
    fi

    # Check for optional dependencies (used in some tests)
    if ! command_exists "gh"; then
        optional_deps+=("gh")
    fi

    if [ ${#optional_deps[@]} -gt 0 ]; then
        echo -e "${YELLOW}Note: Optional dependencies not found (some tests will be skipped):${NC}"
        for dep in "${optional_deps[@]}"; do
            echo -e "  ${YELLOW}⚠${NC} $dep"
        done
        echo ""
    fi

    echo -e "${GREEN}✓ All required dependencies found${NC}"
    echo ""

    return 0
}

#
# Records a test result and updates counters
#
# Arguments:
#   $1 - Test result (0=passed, 1=failed)
# Returns:
#   None
# Side Effects:
#   Updates global PASSED and FAILED counters
#
record_result() {
    local result=$1

    if [ "$result" -eq 0 ]; then
        ((++PASSED))
    else
        ((++FAILED))
    fi
}

#
# Prints the test header banner
#
# Arguments:
#   None
# Returns:
#   None
# Side Effects:
#   Prints to stdout
#
print_header() {
    echo "========================================"
    echo "GitHub Connectivity Test"
    echo -e "Repository: ${BLUE}${REPO}${NC}"
    echo "========================================"
    echo ""
}

#
# Prints the test summary with pass/fail counts
#
# Arguments:
#   None
# Returns:
#   0 if all tests passed, 1 if any failed
# Side Effects:
#   Prints to stdout
#
print_summary() {
    echo "========================================"
    echo "Summary"
    echo "========================================"
    echo -e "Tests Passed: ${GREEN}${PASSED}${NC}"

    if [ ${FAILED} -gt 0 ]; then
        echo -e "Tests Failed: ${RED}${FAILED}${NC}"
    else
        echo -e "Tests Failed: ${FAILED}"
    fi
    echo ""

    if [ ${FAILED} -eq 0 ]; then
        echo -e "${GREEN}✓ All critical tests passed!${NC}"
        echo "GitHub connectivity is working properly."
        return 0
    else
        echo -e "${RED}✗ Some tests failed.${NC}"
        echo "Please review the failures above."
        return 1
    fi
}

################################################################################
# Test Functions
################################################################################

#
# Test 1: DNS Resolution
# Verifies that github.com can be resolved via DNS
#
# Arguments:
#   None
# Returns:
#   None
# Side Effects:
#   Updates test counters, prints to stdout
#
test_dns_resolution() {
    echo "Test 1: DNS Resolution"

    if host github.com >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC} - GitHub DNS resolves successfully"
        record_result 0
    else
        echo -e "${RED}✗ FAILED${NC} - Cannot resolve github.com"
        record_result 1
    fi

    echo ""
}

#
# Test 2: HTTPS Connectivity
# Verifies HTTPS connection to GitHub's main site
#
# Arguments:
#   None
# Returns:
#   None
# Side Effects:
#   Updates test counters, prints to stdout
#
test_https_connectivity() {
    echo "Test 2: HTTPS Connectivity to GitHub"

    if curl -s -I --max-time 10 https://github.com | head -1 | grep -q "200\|301\|302"; then
        echo -e "${GREEN}✓ PASSED${NC} - HTTPS connection successful"
        record_result 0
    else
        echo -e "${RED}✗ FAILED${NC} - Cannot connect via HTTPS"
        record_result 1
    fi

    echo ""
}

#
# Test 3: Repository Accessibility via Public API
# Checks if the repository can be accessed through GitHub's public API
#
# Arguments:
#   None
# Returns:
#   None
# Side Effects:
#   Updates test counters, prints to stdout
#
test_repository_api_access() {
    echo "Test 3: Repository Accessibility (Public API)"

    # -L follows redirects: GitHub returns 301 for renamed or transferred
    # repositories, and the redirect body has no "full_name" field.
    local repo_info
    repo_info=$(curl -sL --max-time 10 "${GITHUB_API_URL}")

    if echo "${repo_info}" | grep -q "\"full_name\""; then
        echo -e "${GREEN}✓ PASSED${NC} - Repository accessible via API"

        # GitHub renders JSON as '"key": "value"' -- the patterns below
        # allow the whitespace after the colon.
        local full_name
        full_name=$(echo "${repo_info}" \
            | grep -oE '"full_name"[[:space:]]*:[[:space:]]*"[^"]*"' \
            | head -1 | cut -d'"' -f4)
        echo "  Repository: ${full_name}"

        local is_private
        is_private=$(echo "${repo_info}" \
            | grep -oE '"private"[[:space:]]*:[[:space:]]*(true|false)' \
            | head -1 | awk -F: '{gsub(/[[:space:]]/, "", $2); print $2}')
        echo "  Private: ${is_private}"

        record_result 0
    else
        echo -e "${RED}✗ FAILED${NC} - Cannot access repository via API"
        record_result 1
    fi

    echo ""
}

#
# Test 4: Git Protocol Connectivity
# Tests git ls-remote functionality to verify git protocol access
#
# Arguments:
#   None
# Returns:
#   None
# Side Effects:
#   Updates test counters, prints to stdout
#
test_git_protocol() {
    echo "Test 4: Git Protocol (ls-remote)"

    if timeout 10 git ls-remote "${GITHUB_URL}" HEAD >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC} - Git ls-remote successful"

        local head_ref
        head_ref=$(git ls-remote "${GITHUB_URL}" HEAD | awk '{print $1}')
        echo "  HEAD commit: ${head_ref:0:8}"

        record_result 0
    else
        echo -e "${RED}✗ FAILED${NC} - Git ls-remote failed"
        record_result 1
    fi

    echo ""
}

#
# Test 5: GitHub CLI Authentication
# Verifies GitHub CLI (gh) is installed and authenticated
#
# Arguments:
#   None
# Returns:
#   None
# Side Effects:
#   Updates test counters, prints to stdout
#
test_gh_authentication() {
    echo "Test 5: GitHub CLI Authentication"

    if command_exists "gh"; then
        if gh auth status >/dev/null 2>&1; then
            echo -e "${GREEN}✓ PASSED${NC} - GitHub CLI authenticated"

            local active_user
            active_user=$(gh auth status 2>&1 | grep "Logged in to github.com account" | head -1 | awk '{print $6}')
            echo "  Active account: ${active_user}"

            record_result 0
        else
            echo -e "${YELLOW}⚠ WARNING${NC} - GitHub CLI not authenticated"
            record_result 1
        fi
    else
        echo -e "${YELLOW}⚠ SKIP${NC} - GitHub CLI (gh) not installed"
    fi

    echo ""
}

#
# Test 6: Repository Access via GitHub CLI
# Verifies repository can be accessed through the gh CLI
#
# Arguments:
#   None
# Returns:
#   None
# Side Effects:
#   Updates test counters, prints to stdout
#
test_gh_repo_access() {
    echo "Test 6: Repository Access via gh CLI"

    if command_exists "gh" && gh auth status >/dev/null 2>&1; then
        if gh repo view "${REPO}" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ PASSED${NC} - Repository accessible via gh CLI"

            local repo_desc
            repo_desc=$(gh repo view "${REPO}" --json description -q .description)
            echo "  Description: ${repo_desc}"

            record_result 0
        else
            echo -e "${RED}✗ FAILED${NC} - Cannot access repository via gh CLI"
            record_result 1
        fi
    else
        echo -e "${YELLOW}⚠ SKIP${NC} - GitHub CLI not available or not authenticated"
    fi

    echo ""
}

#
# Test 7: GitHub API Rate Limits
# Checks current API rate limit status
#
# Arguments:
#   None
# Returns:
#   None
# Side Effects:
#   Updates test counters, prints to stdout
#
test_api_rate_limits() {
    echo "Test 7: GitHub API Rate Limits"

    local rate_limit
    rate_limit=$(curl -sL --max-time 10 https://api.github.com/rate_limit)

    if echo "${rate_limit}" | grep -q "\"limit\""; then
        local remaining
        remaining=$(echo "${rate_limit}" \
            | grep -oE '"remaining"[[:space:]]*:[[:space:]]*[0-9]+' \
            | head -1 | awk -F: '{gsub(/[[:space:]]/, "", $2); print $2}')

        local limit
        limit=$(echo "${rate_limit}" \
            | grep -oE '"limit"[[:space:]]*:[[:space:]]*[0-9]+' \
            | head -1 | awk -F: '{gsub(/[[:space:]]/, "", $2); print $2}')

        echo -e "${GREEN}✓ PASSED${NC} - API rate limit check successful"
        echo "  Rate limit: ${remaining}/${limit} remaining"

        record_result 0
    else
        echo -e "${RED}✗ FAILED${NC} - Cannot check API rate limits"
        record_result 1
    fi

    echo ""
}

#
# Test 8: Latest Release Check
# Verifies access to repository releases via API
#
# Arguments:
#   None
# Returns:
#   None
# Side Effects:
#   Updates test counters, prints to stdout
#
test_latest_release() {
    echo "Test 8: Latest Release Check"

    local releases_url="${GITHUB_API_URL}/releases/latest"

    local release_info
    release_info=$(curl -sL --max-time 10 "${releases_url}")

    if echo "${release_info}" | grep -q "\"tag_name\""; then
        local latest_tag
        latest_tag=$(echo "${release_info}" \
            | grep -oE '"tag_name"[[:space:]]*:[[:space:]]*"[^"]*"' \
            | head -1 | cut -d'"' -f4)

        echo -e "${GREEN}✓ PASSED${NC} - Latest release accessible"
        echo "  Latest release: ${latest_tag}"

        record_result 0
    else
        echo -e "${YELLOW}⚠ WARNING${NC} - Cannot access releases (may not exist)"
    fi

    echo ""
}

################################################################################
# Main Execution
################################################################################

#
# Main function - orchestrates all validation and tests
#
# Arguments:
#   $1 - Repository name (owner/repo format)
# Returns:
#   0 if all tests passed, 1 if any failed
#
main() {
    # Validate command line arguments
    if [ -z "$1" ]; then
        usage
    fi

    REPO="$1"
    GITHUB_URL="https://github.com/${REPO}"
    GITHUB_API_URL="https://api.github.com/repos/${REPO}"

    # Validate repository format
    if ! validate_repo_format "${REPO}"; then
        exit 1
    fi

    # Check for required dependencies
    if ! check_dependencies; then
        exit 1
    fi

    # Print test header
    print_header

    # Run all tests
    test_dns_resolution
    test_https_connectivity
    test_repository_api_access
    test_git_protocol
    test_gh_authentication
    test_gh_repo_access
    test_api_rate_limits
    test_latest_release

    # Print summary and exit with appropriate code
    if print_summary; then
        exit 0
    else
        exit 1
    fi
}

# Execute main function with all script arguments
main "$@"
