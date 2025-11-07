#!/bin/bash -e

###########################################################################
# Constants...
###########################################################################

SOURCE_REMOTE=origin
SOURCE_BRANCH=develop

TARGET_REMOTE=origin
TARGET_BRANCH=main
TARGET_REPO='git@github.com:stewit/dtexp.git'

SOURCE_REMOTE_BRANCH="$SOURCE_REMOTE/$SOURCE_BRANCH"
TARGET_REMOTE_BRANCH="$TARGET_REMOTE/$TARGET_BRANCH"

###########################################################################
# Usage...
###########################################################################

print_usage() {
 echo
 echo "Usage:"
 echo
 echo "  release.sh --help"
 echo "    Displays this help message."
 echo
 echo "  release.sh <VERSION>"
 echo "    Creates (or checks out) a local '$TARGET_BRANCH' branch,"
 echo "    builds, runs checks, tags the commit, pushes to github,"
 echo "    and finally publishes to pypi"
 echo
 echo "  Note: If a local branch named '$TARGET_BRANCH' already exists, it will be overwritten with the content of the remote release branch WITHOUT WARNING!"
 echo
}

if [ "$1" == '-h' ] || [ "$1" == '--help' ]; then
 print_usage
 exit 0
fi

if [[ "$2" == "--dry-run" ]]; then
    DRY_RUN=true
else
    DRY_RUN=false
fi

RELEASE_VERSION="$1"
if [ -z "$RELEASE_VERSION" ]; then
 print_usage
 exit 1
else
 echo
 echo "Releasing version '$RELEASE_VERSION' from '$SOURCE_REMOTE_BRANCH' to '$TARGET_REMOTE_BRANCH'."
fi

###########################################################################
echo
echo "Testing preconditions..."
###########################################################################

# 1. Test presence of the source repository.
echo -n "source remote '$SOURCE_REMOTE'"
REMOTE_ORIGIN=$(git remote get-url "$SOURCE_REMOTE" 2>/dev/null || true)
if [ -z "$REMOTE_ORIGIN" ]; then
 echo " - not ok: missing"
 exit 1
else
 echo " - ok"
fi

# 2. Ensure presence of the correct target repository with correct url.
echo -n "target remote '$TARGET_REMOTE'"
REMOTE_URL=$(git remote get-url "$TARGET_REMOTE" 2>/dev/null || true)
if [ -z "$REMOTE_URL" ]; then
 git remote add "$TARGET_REMOTE" "$TARGET_REPO"
 echo " - ok: added"
elif [ "$REMOTE_URL" == "$TARGET_REPO" ]; then
 echo " - ok"
else
 echo " - not ok: wrong remote URL '$REMOTE_URL'"
 exit 1
fi

git fetch --multiple "$SOURCE_REMOTE" "$TARGET_REMOTE" >/dev/null

# Usage: branch_exists <branch name> --extra --args
branch_exists() {
 EXISTING_BRANCH=$(git branch $2 '--format=%(refname)' --list "$1")
 if [ -n "$EXISTING_BRANCH" ]; then
  return 0
 else
  return 1
 fi
}

# Usage: remote_branch_exists <remote branch name>
remote_branch_exists() {
 branch_exists "$1" --remote
 return $?
}

# Usage: local_branch_exists <local branch name>
local_branch_exists() {
 branch_exists "$1"
 return $?
}

# Checks successful

checks_successful() {
    ./run check
    return $?
}

# 3. Test presence of the source branch
echo -n "remote source branch '$SOURCE_REMOTE_BRANCH'"
if remote_branch_exists "$SOURCE_REMOTE_BRANCH"; then
 echo " - ok"
else
 echo " - not ok: missing"
 exit 1
fi

# 4. Ensure local presence of the target branch.
echo -n "local target branch '$TARGET_BRANCH'"
if remote_branch_exists "$TARGET_REMOTE_BRANCH"; then
 git checkout --quiet -B "$TARGET_BRANCH" "$TARGET_REMOTE_BRANCH"
 echo " - ok: created"
else
 if local_branch_exists "$TARGET_BRANCH"; then
  echo " - ok: checked out'"
  git checkout --quiet "$TARGET_BRANCH"
 else
  git checkout --quiet --orphan "$TARGET_BRANCH"
  echo " - ok: initialized"
 fi
fi

# 5. Test whether the release version already exists.
RELEASE_TAG="v$RELEASE_VERSION"
echo -n "release tag availability '$RELEASE_TAG'"
EXISTING_TAG=$(git tag --list "$RELEASE_TAG") 
if [ -n "$EXISTING_TAG" ]; then
 echo " - not ok: exists"
 exit 1
else
 echo " - ok"
fi

###########################################################################
echo
echo "Preparing release..."
###########################################################################
# git restore --quiet --source "$SOURCE_REMOTE_BRANCH" .

echo "Get newest develop branch from remote"
git checkout --quiet "$SOURCE_BRANCH"
git pull "$SOURCE_REMOTE" "$SOURCE_BRANCH"

echo "Get newest release branch from remote"
git checkout --quiet "$TARGET_BRANCH"
git pull "$TARGET_REMOTE" "$TARGET_BRANCH"

echo "Checkout source branch and merge in target branch"
git checkout --quiet "$SOURCE_BRANCH"
git merge "$TARGET_BRANCH" # i.e. release into develop

# Make sure changelog has been updated
CHANGELOG_DIFF=$(git diff "$SOURCE_BRANCH" "$TARGET_BRANCH" -- CHANGELOG.md)
if [ -z "$CHANGELOG_DIFF" ]; then
    echo "no changelog entry. Aborting. Please edit changelog."
    exit 1
else
    echo "- ok: found changelog edits"
fi

# Check changelog line exists
if grep -Fxq "## $RELEASE_VERSION" CHANGELOG.md; then
    echo "Changelog entry for version $RELEASE_VERSION found."
else
    echo "Changelog entry for version $RELEASE_VERSION not found. Exiting."
fi

# Check version in pyproject.toml
echo "Checking pyproject version against $RELEASE_VERSION"
pyproject_version="$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
if [[ "$pyproject_version" != "$RELEASE_VERSION" ]]; then
    echo "Pyproject version differs from release version $RELEASE_VERSION: $pyproject_version"
    exit 1
else
    echo "- ok: pyproject version agrees with $RELEASE_VERSION."
fi

# Check __version__ in dtexp __init__.py
echo "Checking dtexp __version__ against $RELEASE_VERSION"
dtexp_version="$(uv run python -c 'from dtexp import __version__; print(__version__)' 2>/dev/null)"
if [[ "$dtexp_version" != "$RELEASE_VERSION" ]]; then
    echo "dtexp __version__ differs from release version $RELEASE_VERSION: $dtexp_version"
    exit 1
else
    echo "- ok: dtexp_version __version__ agrees with $RELEASE_VERSION."
fi


# Last check: All checks run
echo -n "Run checks"
if checks_successful; then
 echo " - ok"
else
 echo " - not ok: failed checks. Exiting!"
 exit 1
fi


echo "===> Start build"
rm -r dist
if uv build; then
    echo " - ok: Successfully built dtexp."
else
    echo " - failure: Building dtexp failed"
    exit 1
fi

# Actual release process
echo "===> Starting actual release process"

# Example usage
if $DRY_RUN; then
    echo "Running in dry-run mode. No actual changes will be made. Stopping here."
    exit 0
else
    echo "Waiting for 5 seconds"
    sleep 5
    echo "Proceeding."
fi

echo "add VERSION and CHANGELOG.md"
echo "$RELEASE_VERSION" > VERSION     # Version into version file
# git add --all
git add VERSION CHANGELOG.md
git commit --allow-empty --quiet --message="Release $RELEASE_TAG"
git tag "$RELEASE_TAG"


###########################################################################
echo
echo "Publishing release to remote git repo..."
###########################################################################

git checkout --quiet "$TARGET_BRANCH"
git merge "$SOURCE_BRANCH"
echo "Push release branch"
git push --tags --no-verify "$TARGET_REMOTE" "$TARGET_BRANCH"

git checkout --quiet "$SOURCE_BRANCH"
echo "dev-snapshot-post-$RELEASE_VERSION" > VERSION
git add VERSION
git commit --allow-empty --quiet --message="Post-Release $RELEASE_VERSION dev snapshot"
echo "Push development branch"
git push --tags --no-verify "$SOURCE_REMOTE" "$SOURCE_BRANCH"


###########################################################################
echo
echo "Publishing package to Pypi..."
###########################################################################
echo
echo "You will be asked for username and password."
echo "You have to enter __token__ as username"
echo "You then have to enter the token (including the pypi- at beginning) as password"
echo "The token can be obtained in Pypi UI user account settings / API token."

uv publish ./dist/*