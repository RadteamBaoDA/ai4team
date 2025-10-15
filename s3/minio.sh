#!/usr/bin/env bash
set -euo pipefail

# MinIO Docker launcher script (Linux / macOS)
# Usage examples:
#  ./minio_setup.sh --name node1 --my-name node1 --add-host other:192.168.1.10 --join node2 node3
#  ./minio_setup.sh --name minio-1 --my-name minio-1                 (single node)
#
# Options:
#  --join <node1> <node2> ...    Node hostnames (or IPs) to form a distributed cluster
#  --my-name <name>              Hostname this node will advertise (default: hostname)
#  --add-host name:ip            Extra docker --add-host entries (repeatable)
#  --name <container_name>       Docker container name (default: minio-<my-name>)
#  --port <host_port>            Host port to bind MinIO API (default: 9000)
#  --access <key>                MINIO_ROOT_USER (default minioadmin)
#  --secret <key>                MINIO_ROOT_PASSWORD (default minioadmin)
#  --data-dir <path>             Host data dir (default ./data-<my-name>)
#  --help                        Show this help and exit

MINIO_ROOT_USER=${MINIO_ROOT_USER:-minioadmin}
MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-minioadmin}
PORT=9000
DASHBOARD_PORT=9001
MY_NAME="$(hostname)"
CONTAINER_NAME=""
DATA_DIR=""
JOIN_NODES=()
ADD_HOSTS=()

print_usage() {
  sed -n '/^# /p' "$0" | sed -n '4,18p' >/dev/stderr
}

# parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --join)
      shift
      while [[ $# -gt 0 && $1 != --* ]]; do
        JOIN_NODES+=("$1")
        shift
      done
      ;;
    --my-name)
      MY_NAME="$2"; shift 2
      ;;
    --add-host)
      ADD_HOSTS+=("$2"); shift 2
      ;;
    --name)
      CONTAINER_NAME="$2"; shift 2
      ;;
    --port)
      PORT="$2"; shift 2
      ;;
    --dashboard-port)
      DASHBOARD_PORT="$2"; shift 2
      ;;
    --access)
      MINIO_ROOT_USER="$2"; shift 2
      ;;
    --secret)
      MINIO_ROOT_PASSWORD="$2"; shift 2
      ;;
    --data-dir)
      DATA_DIR="$2"; shift 2
      ;;
    --help|-h)
      print_usage; exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      print_usage
      exit 1
      ;;
  esac
done

# defaults
CONTAINER_NAME=${CONTAINER_NAME:-minio-${MY_NAME}}
DATA_DIR=${DATA_DIR:-"./data-${MY_NAME}"}

# simple checks
if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found. Install Docker and retry." >&2
  exit 1
fi

mkdir -p "$DATA_DIR"

# build docker run options
DOCKER_OPTS=(run -d --restart unless-stopped -p "${PORT}:9000" -p "${DASHBOARD_PORT}:9001" --name "${CONTAINER_NAME}" --hostname "${MY_NAME}")

# add any --add-host mappings
for ah in "${ADD_HOSTS[@]}"; do
  DOCKER_OPTS+=(--add-host "${ah}")
done

# env
DOCKER_OPTS+=(-e "MINIO_ROOT_USER=${MINIO_ROOT_USER}" -e "MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}")

# mount data dir
DOCKER_OPTS+=(-v "${DATA_DIR}:/data")

# build server args
if [[ ${#JOIN_NODES[@]} -gt 0 ]]; then
  # distributed mode: include this node first, then other nodes
  ENDPOINTS=()
  ENDPOINTS+=( "http://${MY_NAME}:9000/data" )
  for n in "${JOIN_NODES[@]}"; do
    ENDPOINTS+=( "http://${n}:9000/data" )
  done
  # docker image + server + endpoints
  DOCKER_OPTS+=(minio/minio server "${ENDPOINTS[@]}")
else
  # single node
  DOCKER_OPTS+=(minio/minio server --console-address ":9001" /data)
fi

echo "Starting MinIO container '${CONTAINER_NAME}'"
echo "  My name: ${MY_NAME}"
echo "  Joined nodes: ${JOIN_NODES[*]:-(none)}"
echo "  Extra add-hosts: ${ADD_HOSTS[*]:-(none)}"
echo "  Data dir: ${DATA_DIR}"
echo "  Port: ${PORT}"
echo "  Dashboard port: ${DASHBOARD_PORT}"

# show final docker command
printf 'docker %q ' "${DOCKER_OPTS[@]}"
echo

# run
docker "${DOCKER_OPTS[@]}"