#!/usr/bin/env bash
#
# One-time setup for DJ Tools on macOS.
#
# Double-click this in Finder (or run ./setup.command) to:
#   1. Verify Homebrew + the command-line audio tools are installed.
#   2. Create a Python virtual environment with mutagen for the key tools.
#
# It is safe to run this more than once.

set -u

DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR" || exit 1

echo "=========================================="
echo "DJ Tools - macOS setup"
echo "=========================================="
echo

# --- Homebrew --------------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
    echo "[!] Homebrew is not installed."
    echo "    Install it from https://brew.sh then re-run this script:"
    echo '      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo
else
    echo "[OK] Homebrew found: $(command -v brew)"
fi

# --- Command-line audio tools ---------------------------------------------
echo
echo "Checking command-line audio tools..."
need_brew=()
for tool in yt-dlp ffmpeg fpcalc; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "  [OK] $tool -> $(command -v "$tool")"
    else
        echo "  [MISSING] $tool"
        case "$tool" in
            fpcalc) need_brew+=("chromaprint") ;;   # fpcalc ships in the chromaprint formula
            *)      need_brew+=("$tool") ;;
        esac
    fi
done

if [ "${#need_brew[@]}" -gt 0 ]; then
    # De-duplicate the formula list.
    formulas="$(printf '%s\n' "${need_brew[@]}" | sort -u | tr '\n' ' ')"
    echo
    echo "Some tools are missing. Install them with:"
    echo "    brew install $formulas"
    echo
    if command -v brew >/dev/null 2>&1; then
        read -r -p "Install them now with Homebrew? (y/N): " ans
        case "$(printf '%s' "$ans" | tr '[:upper:]' '[:lower:]')" in
            y|yes) brew install $formulas ;;
            *)     echo "Skipped. Install them yourself before using crate digger / dedupe." ;;
        esac
    fi
fi

# --- Python venv with mutagen ---------------------------------------------
echo
echo "Setting up the Python environment for the key tools..."
if command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    echo "[!] python3 not found. Install it with 'brew install python' and re-run."
    PY=""
fi

if [ -n "$PY" ]; then
    VENV_DIR="$DIR/musicKeyConversion/.venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment at $VENV_DIR ..."
        "$PY" -m venv "$VENV_DIR"
    else
        echo "[OK] Virtual environment already exists."
    fi
    if [ -x "$VENV_DIR/bin/python" ]; then
        echo "Installing/upgrading mutagen..."
        "$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
        "$VENV_DIR/bin/python" -m pip install --upgrade mutagen
        echo "[OK] mutagen ready."
    fi
fi

echo
echo "=========================================="
echo "Setup complete."
echo "Launch the toolkit with: ./dj_tools_menu.command"
echo "(or double-click dj_tools_menu.command in Finder)"
echo "=========================================="
echo
read -r -p "Press Enter to close..." _
