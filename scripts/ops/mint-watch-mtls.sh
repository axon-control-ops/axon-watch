#!/usr/bin/env bash
# Mint a local internal CA + client/server certs for Axon-X watch mTLS.
# Directive: run once per host, store paths in ~/.config/axon-watch/deployment.env
set -euo pipefail

outdir="${1:-${HOME}/.config/axon-watch/mtls}"
cn_client="${AXON_WATCH_MTLS_CLIENT_CN:-axon-control-plane}"
cn_server="${AXON_WATCH_MTLS_SERVER_CN:-axon-watch}"
days="${AXON_WATCH_MTLS_DAYS:-825}"

mkdir -p "${outdir}"
cd "${outdir}"

if [[ ! -f ca.key ]]; then
  openssl genrsa -out ca.key 4096
  openssl req -x509 -new -nodes -key ca.key -sha256 -days "${days}" \
    -subj "/CN=Axon-X Internal CA" -out ca.crt
fi

if [[ ! -f client.key ]]; then
  openssl genrsa -out client.key 2048
  openssl req -new -key client.key -subj "/CN=${cn_client}" -out client.csr
  openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out client.crt -days "${days}" -sha256
  rm -f client.csr
fi

if [[ ! -f server.key ]]; then
  openssl genrsa -out server.key 2048
  openssl req -new -key server.key -subj "/CN=${cn_server}" -out server.csr
  openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days "${days}" -sha256
  rm -f server.csr
fi

chmod 600 ca.key client.key server.key
chmod 644 ca.crt client.crt server.crt

cat <<EOF

Minted mTLS material in ${outdir}

Add to ~/.config/axon-watch/deployment.env (both control-plane and watch):

AXON_WATCH_INTERNAL_SERVICE_TOKEN=\$(openssl rand -hex 24)
AXON_WATCH_MTLS_REQUIRED=1
AXON_WATCH_MTLS_CA_FILE=${outdir}/ca.crt
AXON_WATCH_MTLS_CLIENT_CERT=${outdir}/client.crt
AXON_WATCH_MTLS_CLIENT_KEY=${outdir}/client.key
AXON_WATCH_MTLS_ALLOWED_CN=${cn_client}

Reverse proxy MUST set on watch requests:
  X-SSL-Client-Verify: SUCCESS
  X-SSL-Client-S-DN: CN=${cn_client}

Then: axonrestart
EOF
