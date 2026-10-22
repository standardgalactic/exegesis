#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/exegesis"

REPO="standardgalactic/exegesis"

# 1. Verify GitHub authentication.
gh auth status

# 2. Create a permissive MIT license.
cat > LICENSE <<'EOF'
MIT License

Copyright (c) 2026 Flyxion

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

# 3. Exclude local data and generated artifacts.
cat >> .gitignore <<'EOF'

# Local corpus and model outputs
/data/
/logs/

# Python environments and caches
.venv/
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.ruff_cache/

# Local configuration and secrets
.env
.env.*
!.env.example

# Temporary files
*.tmp
*.log
EOF

# 4. Initialize Git if needed.
if [[ ! -d .git ]]; then
    git init
fi

git branch -M main

# 5. Check for unexpectedly large files before staging.
echo
echo "Repository files:"
find . -type f \
    -not -path './.git/*' \
    -not -path './.venv/*' \
    -not -path './data/*' \
    -not -path './logs/*' \
    -size +20M -print

# 6. Stage and review.
git add -A

echo
echo "Staged files:"
git diff --cached --stat

echo
echo "Checking for accidentally staged corpus files..."
if git diff --cached --name-only |
    grep -E '^(data/|logs/|\.venv/)'; then
    echo "ERROR: Generated data was staged. Aborting."
    exit 1
fi

# 7. Commit.
if ! git diff --cached --quiet; then
    git commit -m "Initial release: local-first scholarly corpus analysis"
else
    echo "Nothing new to commit."
fi

# 8. Create the remote repository if absent.
if gh repo view "$REPO" >/dev/null 2>&1; then
    echo "GitHub repository already exists."
else
    gh repo create "$REPO" \
        --public \
        --description "Local-first scholarly corpus discovery, extraction, and model-assisted analysis"
fi

# 9. Configure origin.
URL="git@github.com:${REPO}.git"

if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$URL"
else
    git remote add origin "$URL"
fi

# 10. Publish.
git push -u origin main

echo
echo "Published successfully:"
echo "https://github.com/$REPO"
