#!/bin/bash
#
# Thermomix CLI uninstaller (macOS).
#
# Removes only what the installer created:
#   ~/.local/share/thermomix-cli   the app folder (marked as ours)
#   ~/.local/bin/thermomix-cli     the command shim (marked as ours)
#   the one marked line in ~/.zshrc (or ~/.bash_profile)
#
# Your saved Cookidoo email and password are a separate, explicit choice:
#   --remove-credentials   also delete ~/.config/thermomix-cli/config.json
#   --keep-credentials     leave them in place without asking
# With neither flag it asks, and keeps them if it cannot ask.
#
# Your Cookidoo account, your recipes and your Thermomix are never touched.
# Running this twice is safe.

set -euo pipefail

APP_HOME="${THERMOMIX_CLI_HOME:-$HOME/.local/share/thermomix-cli}"
BIN_DIR="${THERMOMIX_CLI_BIN:-$HOME/.local/bin}"
CONFIG_FILE="${THERMOMIX_CLI_CONFIG:-$HOME/.config/thermomix-cli/config.json}"

MARKER_FILE=".thermomix-cli-install"
SHIM_MARKER="# thermomix-cli launcher – safe to delete"
RC_MARKER="# added by thermomix-cli installer"

CREDENTIALS="ask"
for arg in "$@"; do
  case "$arg" in
    --remove-credentials) CREDENTIALS="remove" ;;
    --keep-credentials)   CREDENTIALS="keep" ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }

say ""
say "Removing Thermomix CLI"
say ""

# ── the app folder ──────────────────────────────────────────────────────────
if [ -L "$APP_HOME" ]; then
  # Deleting the link would report success while leaving everything it points
  # at behind. The installer refuses these, so this one is not ours.
  say "skipped  $APP_HOME – it is a symbolic link, so it is left alone"
  say "         whatever it points at was not installed by this installer"
elif [ -d "$APP_HOME" ]; then
  if [ -e "$APP_HOME/$MARKER_FILE" ]; then
    rm -rf "$APP_HOME"
    say "removed  $APP_HOME"
  else
    say "skipped  $APP_HOME – it was not created by the installer, so it is left alone"
  fi
else
  say "skipped  $APP_HOME – not there"
fi

# ── the command ─────────────────────────────────────────────────────────────
SHIM="$BIN_DIR/thermomix-cli"
if [ -L "$SHIM" ]; then
  say "skipped  $SHIM – it is a symbolic link, so it is left alone"
elif [ -e "$SHIM" ]; then
  if grep -qF "$SHIM_MARKER" "$SHIM" 2>/dev/null; then
    rm -f "$SHIM"
    say "removed  $SHIM"
  else
    say "skipped  $SHIM – it is not the installer's launcher, so it is left alone"
  fi
else
  say "skipped  $SHIM – not there"
fi

# ── the PATH line ───────────────────────────────────────────────────────────
for RC in "$HOME/.zshrc" "$HOME/.bash_profile"; do
  if [ -f "$RC" ] && grep -qF "$RC_MARKER" "$RC"; then
    TMP="$(mktemp "${TMPDIR:-/tmp}/thermomix-cli-rc.XXXXXX")"
    # Drop the marker line and the single export line that follows it.
    awk -v marker="$RC_MARKER" '
      $0 == marker { skip = 2; next }
      skip > 0 && $0 ~ /^export PATH=/ { skip = 0; next }
      { skip = 0; print }
    ' "$RC" > "$TMP"
    cat "$TMP" > "$RC"
    rm -f "$TMP"
    say "cleaned  $RC"
  fi
done

# ── the saved Cookidoo details ──────────────────────────────────────────────
say ""
if [ ! -f "$CONFIG_FILE" ]; then
  say "no saved Cookidoo details to remove"
else
  if [ "$CREDENTIALS" = "ask" ]; then
    if [ -t 0 ]; then
      printf 'Also delete your saved Cookidoo email and password (%s)? [y/N] ' "$CONFIG_FILE"
      read -r answer
      case "$answer" in [yY]*) CREDENTIALS="remove" ;; *) CREDENTIALS="keep" ;; esac
    else
      CREDENTIALS="keep"
    fi
  fi
  if [ "$CREDENTIALS" = "remove" ]; then
    rm -f "$CONFIG_FILE"
    rmdir "$(dirname "$CONFIG_FILE")" 2>/dev/null || true
    say "removed  $CONFIG_FILE"
  else
    say "kept     $CONFIG_FILE"
    say "         delete it yourself with:  rm \"$CONFIG_FILE\""
  fi
fi

say ""
say "Done. Your Cookidoo account and your recipes are untouched."
say "Close and reopen Terminal to finish tidying up."
say ""
