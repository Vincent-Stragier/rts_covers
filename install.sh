#!/bin/bash
# chmod +x install.sh & chmod 777 install.sh

# Check for sudo permissions
if [ $EUID != 0 ]; then
    sudo "$0" "$@"
    exit $?
fi

# Get installation path
SOURCE="${BASH_SOURCE:-0}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
    DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

FILE="${DIR}/settings.json"
if [ -f "$FILE" ]; then
    echo "$FILE exists (you can edit the settings later, using this file)"
else
    cp "${DIR}/settings_default.json" "${DIR}/settings.json"
    echo "You must edit the settings in: ${FILE}."
fi

TEMPLATE="${DIR}/rts_covers.service"
PATH="${DIR}"

# Install requirements
sudo apt install python3-pip python3-dev build-essential libsystemd-dev python3-as-python -y
python -m pip install wheel -U
python -m venv --system-site-packages ${PATH}/.venv

${PATH}/.venv/bin/pip install -r requirements.txt

# Add service and start it
systemctl stop rts_covers
sed -e "s|\${path}|${PATH}|g" "${TEMPLATE}" > "/lib/systemd/system/rts_covers.service"
systemctl daemon-reload
systemctl enable rts_covers
systemctl start rts_covers

echo "All done."
