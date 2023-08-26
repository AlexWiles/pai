#!/bin/bash

# Check if the user is authenticated with GitHub CLI
if ! gh auth status >/dev/null 2>&1; then
    echo "You need to authenticate with GitHub CLI (gh) first. Run 'gh auth login'."
    exit 1
fi

# 1. Update the version in pyproject.toml
echo "Enter the new version (e.g., 1.0.0): "
read VERSION

# Update the version using poetry
poetry version $VERSION

# 2. Update CHANGELOG.md using Git commit history
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null) # Gets the latest tag
if [ -z "$LAST_TAG" ]; then
    # If no previous tags, get all commits
    CHANGES=$(git log --pretty=format:"- %s" --reverse)
else
    # Else, get commits since the last tag
    CHANGES=$(git log ${LAST_TAG}..HEAD --pretty=format:"- %s" --reverse)
fi

# Create or append to CHANGELOG.md
if [ ! -f CHANGELOG.md ]; then
    touch CHANGELOG.md
fi

# Format the changes and append to the changelog
echo -e "\n## Version $VERSION - $(date +"%Y-%m-%d")\n$CHANGES" >> CHANGELOG.md

# 3. Commit the changes
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to $VERSION and update changelog"

# 4. Tag the commit
git tag $VERSION

# 5. Push to GitHub (including tags)
git push origin master --tags

# 6. Create a GitHub release using the GitHub CLI
gh release create $VERSION --title "Release $VERSION" --notes "Release notes for version $VERSION"

# 7. Build and Publish to PyPI
poetry publish --build
