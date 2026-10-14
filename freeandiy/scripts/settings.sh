#!/usr/bin/env bash
# Modified-by: FreeANDIY (Free Andy Agency), 2026. New file, not part of upstream.
# Print this app's settings as KEY=value lines for CI:  freeandiy/scripts/settings.sh >> "$GITHUB_ENV"
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
echo "FA_NAME=$(fa_get this.name)"
echo "FA_REPO=$(fa_get this.repo)"
echo "FA_UPSTREAM_NAME=$(fa_get this.upstream_name)"
echo "FA_BINS=$(fa_get build.bins)"
echo "FA_FEATURES=$(fa_get build.features "")"
echo "FA_TEST_ENV=$(fa_get build.test_env "")"
echo "FA_WEB_ENV=$(fa_get build.web_env "")"
echo "FA_CI_TESTS=$(fa_get build.ci_tests false)"
echo "FA_TESTS=$(fa_get build.tests "")"
# Built executables (names after the rename patch), checked for upstream branding.
echo "FA_EXES=$(fa_get build.exes "$(fa_get this.repo) $(fa_get this.repo)-cli")"
