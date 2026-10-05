#!/bin/sh
# Container entry point: one word selects the process (docs: deploy/README.md).
#   api        serve the HTTP API on $PORT (Cloud Run sets PORT)
#   worker     run attestation jobs until the task deadline
#   tick       one dispatcher / recovery pass, then exit
#   migrate    apply pending migrations (suncly db migrate), then exit
set -eu
case "${1:-api}" in
  api)     exec suncly api serve --host 0.0.0.0 --port "${PORT:-8080}" ;;
  worker)  exec suncly worker run ;;
  tick)    exec suncly worker tick ;;
  migrate) exec suncly db migrate ;;
  *)       exec "$@" ;;
esac
