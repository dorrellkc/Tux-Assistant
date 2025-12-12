#!/bin/sh
PATH="/bin:/usr/bin:/sbin:/usr/sbin"
_ARCHS=$(dpkg --print-architecture && dpkg --print-foreign-architectures)

if ! echo "$_ARCHS" | grep -E 'arm64|amd64' 1>/dev/null 2>/dev/null; then
    echo "Unsupported architecture. $( echo "$_ARCHS" | tr '\n' ' ')"
    exit 1
fi

SUDO="sudo"
if [ "$(id -u)" = "0" ]; then
    SUDO=
fi
sudo -k

echo "This script requires superuser access to install apt package."

set -ex

$SUDO apt-get remove -y surfshark surfshark-release || true

$SUDO tee /etc/apt/trusted.gpg.d/surfshark.asc << PGP_KEY
-----BEGIN PGP PUBLIC KEY BLOCK-----

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
=uoDp
-----END PGP PUBLIC KEY BLOCK-----
PGP_KEY
echo "deb https://ocean.surfshark.com/debian stretch main" | $SUDO tee /etc/apt/sources.list.d/surfshark.list
$SUDO apt-get update
$SUDO apt-get install -y surfshark

set +x

echo ""
echo "Surfshark was successfully installed."
echo ""
### END OF SCRIPT