#!/bin/bash

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
git push origin main --tags

# 7. Build and Publish to PyPI
poetry publish --build