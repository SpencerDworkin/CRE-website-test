#!/usr/bin/env bash
# Wraps the artifact-ready body (src/rad-squad.body.html) into a standalone
# index.html that can be opened directly from disk or served statically.
set -euo pipefail
cd "$(dirname "$0")"
{
  echo '<!doctype html>'
  echo '<html lang="en">'
  echo '<head>'
  echo '<meta charset="utf-8">'
  echo '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
  echo '<meta name="description" content="RAD Squad Tactics — an original turn-based squad tactics game.">'
  echo '<meta name="color-scheme" content="dark">'
  sed -n '1,4p' src/rad-squad.body.html
  echo '</head>'
  echo '<body>'
  sed -n '5,$p' src/rad-squad.body.html
  echo '</body>'
  echo '</html>'
} > index.html
echo "built index.html ($(wc -l < index.html) lines)"
