#!/bin/bash
#
# Thermomix CLI installer (macOS).
#
# Run it again any time to update – it is safe to repeat and always ends in the
# same place. It never asks for your password, never uses sudo, and never
# changes anything outside the two folders it owns:
#
#   ~/.local/share/thermomix-cli   the app, its Python and its packages
#   ~/.local/bin/thermomix-cli     the command you type
#
# It also adds one marked line to ~/.zshrc so the command can be found. The
# uninstaller removes all three.
#
# Environment overrides (you do not normally need these):
#   THERMOMIX_CLI_HOME     where the app is installed
#   THERMOMIX_CLI_BIN      where the command shim goes
#   THERMOMIX_CLI_SOURCE   a local folder or tarball URL to install from
#   THERMOMIX_CLI_NO_PATH  set to 1 to skip the ~/.zshrc line

set -euo pipefail

REPO_URL="https://github.com/iamjoewills/thermomix-cli"
APP_HOME="${THERMOMIX_CLI_HOME:-$HOME/.local/share/thermomix-cli}"
BIN_DIR="${THERMOMIX_CLI_BIN:-$HOME/.local/bin}"
SOURCE="${THERMOMIX_CLI_SOURCE:-$REPO_URL/archive/refs/heads/main.tar.gz}"
PYTHON_VERSION="3.12"

# uv (https://github.com/astral-sh/uv) is Astral's Python installer. It is
# pinned to one release and checked against the SHA-256 published with it, so
# this script installs exactly the binary it expects or stops.
UV_VERSION="0.12.13"
UV_SHA256_ARM64="7e6ddb9316acc00f2296c82ff4d99977870ee34b2f0ddcae9444d714db9364ed"
UV_SHA256_X86_64="5e287ef61cb6a9b61b3a83fef124fd143e400468a7dac794230147a810e17119"

MARKER_FILE=".thermomix-cli-install"
SHIM_MARKER="# thermomix-cli launcher – safe to delete"
RC_MARKER="# added by thermomix-cli installer"

say()  { printf '%s\n' "$*"; }
step() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nSomething stopped the install:\n  %s\n\n' "$*" >&2; exit 1; }

# ── checks ──────────────────────────────────────────────────────────────────
[ "$(uname -s)" = "Darwin" ] || fail "This installer is for macOS. See the README for other systems."

case "$(uname -m)" in
  arm64)  UV_ASSET="uv-aarch64-apple-darwin"; UV_SHA256="$UV_SHA256_ARM64" ;;
  x86_64) UV_ASSET="uv-x86_64-apple-darwin";  UV_SHA256="$UV_SHA256_X86_64" ;;
  *)      fail "Unrecognised Mac processor: $(uname -m)" ;;
esac

for tool in curl tar shasum mktemp; do
  command -v "$tool" >/dev/null 2>&1 || fail "'$tool' is missing from this Mac, which is unusual. Nothing was changed."
done

# A symbolic link would be followed here and then only half-removed by the
# uninstaller, stranding everything it points at. Refuse it instead.
if [ -L "$APP_HOME" ]; then
  fail "$APP_HOME is a symbolic link.
  Nothing was changed. Set THERMOMIX_CLI_HOME to a real folder."
fi
if [ -L "$BIN_DIR/thermomix-cli" ]; then
  fail "$BIN_DIR/thermomix-cli is a symbolic link.
  Nothing was changed. Remove it, or set THERMOMIX_CLI_BIN to somewhere else."
fi

# Refuse to touch a folder we did not create.
if [ -e "$APP_HOME" ] && [ ! -e "$APP_HOME/$MARKER_FILE" ]; then
  if [ -n "$(ls -A "$APP_HOME" 2>/dev/null)" ]; then
    fail "$APP_HOME already exists and was not created by this installer.
  Nothing was changed. Move that folder aside, or set THERMOMIX_CLI_HOME to somewhere else."
  fi
fi

if [ -e "$BIN_DIR/thermomix-cli" ] && ! grep -qF "$SHIM_MARKER" "$BIN_DIR/thermomix-cli" 2>/dev/null; then
  fail "$BIN_DIR/thermomix-cli already exists and is something else.
  Nothing was changed. Rename it, or set THERMOMIX_CLI_BIN to somewhere else."
fi

# The place the working copy is parked while a new one is built. It has to be a
# real folder of ours, because the whole point is being able to move it back.
PREV="$APP_HOME/venv.prev"
if [ -L "$PREV" ]; then
  fail "$PREV is a symbolic link, so the previous version could not be kept safely.
  Nothing was changed. Remove it and run this again."
fi
if [ -e "$PREV" ] && [ ! -d "$PREV" ]; then
  fail "$PREV already exists and is not a folder this installer can use.
  Nothing was changed. Move it aside and run this again."
fi

PARKED=0
restore_previous() {
  rm -rf "$APP_HOME/venv"
  if [ -d "$PREV" ]; then
    # Back to the original path: a Python environment has that path written
    # into its own scripts, so anywhere else would not run.
    mv "$PREV" "$APP_HOME/venv"
  fi
  PARKED=0
}

WORK="$(mktemp -d "${TMPDIR:-/tmp}/thermomix-cli-install.XXXXXX")"
cleanup() {
  rm -rf "$WORK"
  [ "$PARKED" = "1" ] && restore_previous
  return 0
}
trap cleanup EXIT

say ""
say "Thermomix CLI installer"
say "-----------------------"
say "Cookidoo has no official public API. This is an unofficial tool: it is not"
say "supported or endorsed by Vorwerk and it can stop working at any time."
say ""
say "Installing to  $APP_HOME"
say "Command goes to $BIN_DIR/thermomix-cli"

mkdir -p "$APP_HOME" "$BIN_DIR"
: > "$APP_HOME/$MARKER_FILE"
chmod 700 "$APP_HOME"

# ── 1. Python, provided by uv ───────────────────────────────────────────────
step "Getting the Python this tool needs (nothing already on your Mac is changed)"

UV_BIN="$APP_HOME/tools/uv"
UV_STAMP="$APP_HOME/tools/uv.version"

if [ ! -x "$UV_BIN" ] || [ "$(cat "$UV_STAMP" 2>/dev/null || true)" != "$UV_VERSION" ]; then
  UV_URL="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${UV_ASSET}.tar.gz"
  say "    downloading uv ${UV_VERSION}"
  curl -fsSL --retry 3 "$UV_URL" -o "$WORK/uv.tar.gz" \
    || fail "Could not download uv from GitHub. Check your internet connection and try again."

  say "    checking it is the file we expect"
  ACTUAL="$(shasum -a 256 "$WORK/uv.tar.gz" | awk '{print $1}')"
  [ "$ACTUAL" = "$UV_SHA256" ] \
    || fail "The downloaded uv did not match its published checksum.
  Expected $UV_SHA256
  Got      $ACTUAL
  Nothing was installed."

  tar -xzf "$WORK/uv.tar.gz" -C "$WORK"
  mkdir -p "$APP_HOME/tools"
  mv -f "$WORK/$UV_ASSET/uv" "$UV_BIN"
  chmod 755 "$UV_BIN"
  printf '%s\n' "$UV_VERSION" > "$UV_STAMP"
else
  say "    uv ${UV_VERSION} already here"
fi

# Keep everything uv does inside our own folder, so uninstalling really does
# remove it and an existing uv on this Mac is left completely alone.
export UV_PYTHON_INSTALL_DIR="$APP_HOME/python"
export UV_CACHE_DIR="$APP_HOME/cache"
export UV_TOOL_DIR="$APP_HOME/uv-tools"
export UV_NO_CONFIG=1

"$UV_BIN" python install "$PYTHON_VERSION" >/dev/null 2>&1 \
  || fail "Could not download Python $PYTHON_VERSION. Check your internet connection and try again."
say "    Python $PYTHON_VERSION ready"

# ── 2. The tool itself ──────────────────────────────────────────────────────
step "Installing Thermomix CLI"

# A hard kill – a crash, a power cut – can leave both a parked copy and a
# half-built current one. Deciding between them on whether the folder exists is
# not enough, and neither is the executable bit: a partly-installed environment
# has the file there and still fails the moment it tries to import anything. So
# ask the only question that settles it, and run the thing.
venv_runs() {
  [ -x "$APP_HOME/venv/bin/thermomix-cli" ] || return 1
  "$APP_HOME/venv/bin/thermomix-cli" version >/dev/null 2>&1
}

# Start this run from a known place. The parked copy is only let go once the
# current one has proved it can run.
if [ -d "$PREV" ]; then
  if venv_runs; then
    rm -rf "$PREV"
  else
    say "    putting back the copy an interrupted run left parked"
    rm -rf "$APP_HOME/venv"
    mv "$PREV" "$APP_HOME/venv"
  fi
fi

if [ -d "$SOURCE" ]; then
  SRC_DIR="$SOURCE"
  say "    from $SRC_DIR"
else
  say "    downloading the source"
  curl -fsSL --retry 3 "$SOURCE" -o "$WORK/src.tar.gz" \
    || fail "Could not download the source from $SOURCE"
  mkdir -p "$WORK/src"
  tar -xzf "$WORK/src.tar.gz" -C "$WORK/src"
  SRC_DIR="$(find "$WORK/src" -maxdepth 2 -name pyproject.toml -print -quit | xargs -I{} dirname {})"
  [ -n "$SRC_DIR" ] || fail "The downloaded archive did not contain the tool."
fi

# Keep the working copy until the new one has proved itself. If anything below
# fails – a dependency that will not resolve, a dropped connection, a Ctrl-C –
# the trap puts it back at its original path and the command keeps working.
FAIL_HINT=""
if [ -d "$APP_HOME/venv" ]; then
  if venv_runs; then
    mv "$APP_HOME/venv" "$PREV"
    PARKED=1
    FAIL_HINT="
  Your existing version has been put back and still works."
  else
    # Do not promise someone their old version is fine when it is not. There
    # was something here, it did not run, and it is not worth keeping.
    rm -rf "$APP_HOME/venv"
    FAIL_HINT="
  The copy that was already here did not run, so nothing was kept."
  fi
else
  FAIL_HINT="
  Nothing was installed."
fi

# Install against the versions this release was tested with, when the source
# ships them. Without the file, resolve freely rather than refuse to install.
#
# An array rather than a string, so the shell keeps each argument whole: a
# source folder like ~/Downloads/Thermomix CLI is an ordinary place to land.
# ${a[@]+"${a[@]}"} is the guarded expansion bash 3.2 needs under `set -u`.
CONSTRAINTS=()
[ -f "$SRC_DIR/requirements.lock" ] && CONSTRAINTS=(--constraint requirements.lock)

"$UV_BIN" venv --python "$PYTHON_VERSION" "$APP_HOME/venv" >/dev/null 2>&1 \
  || fail "Could not create the app's private Python folder.$FAIL_HINT"

# Run from inside the source folder. uv's own argument parsing splits a
# --constraint path on spaces however carefully the shell quotes it, so it is
# handed a bare filename that has nothing to split. Everything else here is an
# absolute path, which uv handles fine, and the subshell keeps the change of
# directory to itself.
( cd "$SRC_DIR" && "$UV_BIN" pip install --quiet \
    --python "$APP_HOME/venv/bin/python" \
    ${CONSTRAINTS[@]+"${CONSTRAINTS[@]}"} . ) \
  || fail "Could not install Thermomix CLI and its dependencies.$FAIL_HINT"

# ── 3. The command you type ─────────────────────────────────────────────────
step "Adding the thermomix-cli command"

cat > "$BIN_DIR/thermomix-cli" <<SHIM
#!/bin/bash
$SHIM_MARKER
exec "$APP_HOME/venv/bin/thermomix-cli" "\$@"
SHIM
chmod 755 "$BIN_DIR/thermomix-cli"

if [ "${THERMOMIX_CLI_NO_PATH:-0}" != "1" ]; then
  case ":$PATH:" in
    *":$BIN_DIR:"*) say "    $BIN_DIR is already on your PATH" ;;
    *)
      RC="$HOME/.zshrc"
      case "${SHELL:-}" in */bash) RC="$HOME/.bash_profile" ;; esac
      if [ -f "$RC" ] && grep -qF "$RC_MARKER" "$RC"; then
        say "    $RC already has the line"
      else
        printf '\n%s\nexport PATH="%s:$PATH"\n' "$RC_MARKER" "$BIN_DIR" >> "$RC"
        say "    added one line to $RC"
      fi
      export PATH="$BIN_DIR:$PATH"
      ;;
  esac
fi

# ── 4. Prove it ─────────────────────────────────────────────────────────────
step "Checking it works"
INSTALLED="$("$BIN_DIR/thermomix-cli" version)" \
  || fail "The tool installed but would not run.$FAIL_HINT
  Nothing on your Cookidoo account was touched."
say "    $INSTALLED"

# It ran. Only now is the old copy safe to let go of.
PARKED=0
rm -rf "$PREV"

cat > "$APP_HOME/install-receipt.txt" <<RECEIPT
$INSTALLED
installed: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
source:    $SOURCE
uv:        $UV_VERSION ($UV_ASSET)
python:    $PYTHON_VERSION
app home:  $APP_HOME
command:   $BIN_DIR/thermomix-cli
RECEIPT

say ""
say "Done."
say ""
say "Open a NEW Terminal window, then run:"
say ""
say "    thermomix-cli setup"
say ""
say "That asks for your Cookidoo email and password and saves them privately on"
say "this Mac. Then run 'thermomix-cli auth whoami' to check it worked."
say ""
