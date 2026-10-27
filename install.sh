#!/usr/bin/env bash
# Install the competitor-intel skill as a personal Claude Code skill.
# Usage: ./install.sh            (installs to ~/.claude/skills)
#        ./install.sh --project  (installs to ./.claude/skills in the current directory)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="$HOME/.claude/skills"
[[ "${1:-}" == "--project" ]] && dest="$PWD/.claude/skills"
mkdir -p "$dest"
rm -rf "$dest/competitor-intel"
cp -R "$here/skills/competitor-intel" "$dest/competitor-intel"
chmod +x "$dest/competitor-intel/scripts/intel.py"
python3 "$dest/competitor-intel/scripts/intel.py" list >/dev/null
echo "Installed to $dest/competitor-intel"
echo "Next: open Claude and say \"set up a competitor watch\"."
