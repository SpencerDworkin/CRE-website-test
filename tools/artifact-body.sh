#!/usr/bin/env bash
# Strips the standalone HTML wrapper off index.html, leaving just the page body
# (title, styles, markup, script) for embedding into a host page.
set -euo pipefail
cd "$(dirname "$0")/.."
sed -e '/^<!doctype html>$/d' -e '/^<html lang="en">$/d' -e '/^<\/html>$/d' \
    -e '/^<head>$/d' -e '/^<\/head>$/d' -e '/^<body>$/d' -e '/^<\/body>$/d' \
    -e '/^<meta /d' index.html > "${1:-artifact-body.html}"
echo "wrote ${1:-artifact-body.html}"
