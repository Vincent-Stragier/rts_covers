#!/bin/sh
# Install rts_covers (Debian/Ubuntu with systemd, or Alpine Linux with OpenRC).
# Usage: sh ./install.sh

set -eu

# Check for root permissions
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then exec sudo sh "$0" "$@"; fi
    if command -v doas >/dev/null 2>&1; then exec doas sh "$0" "$@"; fi
    echo "Please run this script as root." >&2
    exit 1
fi

# Get installation path (follows symlinks)
DIR="$(cd -P "$(dirname "$(readlink -f "$0")")" && pwd)"

if [ -f "${DIR}/settings.json" ]; then
    echo "${DIR}/settings.json exists (you can edit the settings later, using this file)"
else
    cp "${DIR}/settings_default.json" "${DIR}/settings.json"
    echo "You must edit the settings in: ${DIR}/settings.json."
fi

# Detect the platform
if [ -f /etc/alpine-release ]; then
    PLATFORM=alpine
elif command -v systemctl >/dev/null 2>&1; then
    PLATFORM=systemd
else
    echo "Unsupported platform (need Alpine/OpenRC or a systemd distribution)." >&2
    exit 1
fi

# Install system packages
if [ "$PLATFORM" = alpine ]; then
    apk add --no-cache python3 py3-pip py3-virtualenv python3-dev build-base usbutils
else
    apt-get install -y python3-pip python3-dev build-essential libsystemd-dev python3-as-python python3-venv
fi

# Virtualenv (Alpine's pip is "externally managed", so a venv is required)
python3 -m venv --system-site-packages "${DIR}/.venv"
"${DIR}/.venv/bin/pip" install -U wheel

if [ "$PLATFORM" = alpine ]; then
    # systemd-python is not available/needed on Alpine (logging falls back to syslog)
    grep -vi '^systemd-python' "${DIR}/requirements.txt" > "${DIR}/.requirements.tmp"
    "${DIR}/.venv/bin/pip" install -r "${DIR}/.requirements.tmp"
    rm -f "${DIR}/.requirements.tmp"

    # OpenRC service
    if rc-service rts_covers status >/dev/null 2>&1; then
        rc-service rts_covers stop || true
    fi
    sed -e "s|\${path}|${DIR}|g" "${DIR}/rts_covers.openrc" > /etc/init.d/rts_covers
    chmod 755 /etc/init.d/rts_covers
    rc-update add rts_covers default
    rc-service rts_covers start
else
    "${DIR}/.venv/bin/pip" install -r "${DIR}/requirements.txt"

    # systemd service
    systemctl stop rts_covers 2>/dev/null || true
    sed -e "s|\${path}|${DIR}|g" "${DIR}/rts_covers.service" > /lib/systemd/system/rts_covers.service
    systemctl daemon-reload
    systemctl enable rts_covers
    systemctl start rts_covers
fi

echo "All done."
