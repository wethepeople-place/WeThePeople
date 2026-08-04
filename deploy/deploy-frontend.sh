#!/bin/bash
# =============================================================================
# WeThePeople - Frontend Deployment Reference
# =============================================================================
# The frontend deploys automatically to GitHub Pages on every relevant push
# to main. This script is a reference; no manual steps are normally needed.
#
# GitHub Pages configuration:
#   - Workflow: .github/workflows/deploy-app-pages.yml
#   - Root directory: frontend
#   - Build command: npm run build
#   - Output directory: frontend/dist
#   - Node.js version: 20.x
# =============================================================================

set -euo pipefail

echo "=== WeThePeople Frontend Deploy ==="
echo ""
echo "The frontend auto-deploys via GitHub Pages on push to main."
echo ""
echo "Current deployment:"
echo "  URL:    https://app.wethepeople.place"
echo "  Source: GitHub Actions -> GitHub Pages"
echo "  Root:   frontend/"
echo ""
echo "To trigger a deploy: push a frontend or workflow change to main."
echo ""
echo "To check deploy status:"
echo "  gh run list --workflow deploy-app-pages.yml"
