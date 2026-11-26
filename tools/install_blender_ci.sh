#!/usr/bin/env bash
set -euo pipefail

# Reproducible authoring toolchain for the A-Square asset pipeline.
# Try Blender's official mirror first, then its canonical host, then the NJU
# mirror. Every candidate is checked against a SHA-256 release manifest before
# extraction; no unverified archive is ever executed.
BLENDER_VERSION="${BLENDER_VERSION:-5.2.4}"
BLENDER_SERIES="Blender5.2"
ARCHIVE_NAME="blender-${BLENDER_VERSION}-linux-x64.tar.xz"
CHECKSUM_NAME="blender-${BLENDER_VERSION}.sha256"
RUNNER_TEMP_DIR="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
INSTALL_ROOT="${BLENDER_INSTALL_ROOT:-${RUNNER_TEMP_DIR}/blender-${BLENDER_VERSION}}"
BLENDER_DIR="${INSTALL_ROOT}/blender-${BLENDER_VERSION}-linux-x64"
BLENDER_BIN="${BLENDER_DIR}/blender"

if [[ "${BLENDER_VERSION}" != "5.2.4" ]]; then
  echo "This project currently validates Blender 5.2.4 LTS; refusing an unreviewed version: ${BLENDER_VERSION}" >&2
  exit 2
fi

fetch_first_available() {
  local output="$1"
  shift
  local url
  for url in "$@"; do
    echo "Trying verified Blender distribution source: ${url}" >&2
    if curl --fail --location --silent --show-error \
      --connect-timeout 25 --max-time 1800 --retry 1 --retry-delay 2 \
      "${url}" -o "${output}"; then
      if [[ -s "${output}" ]]; then
        echo "Downloaded from ${url}" >&2
        return 0
      fi
    fi
    rm -f "${output}"
  done
  echo "All configured Blender distribution mirrors failed." >&2
  return 1
}

if [[ ! -x "${BLENDER_BIN}" ]]; then
  mkdir -p "${INSTALL_ROOT}"
  DOWNLOAD_DIR="$(mktemp -d "${RUNNER_TEMP_DIR}/blender-download.XXXXXX")"
  trap 'rm -rf "${DOWNLOAD_DIR}"' EXIT

  OFFICIAL_BASE="https://download.blender.org/release/${BLENDER_SERIES}"
  OFFICIAL_MIRROR_BASE="https://mirror.blender.org/release/${BLENDER_SERIES}"
  NJU_MIRROR_BASE="https://mirror.nju.edu.cn/blender/release/${BLENDER_SERIES}"

  fetch_first_available "${DOWNLOAD_DIR}/${CHECKSUM_NAME}" \
    "${OFFICIAL_BASE}/${CHECKSUM_NAME}" \
    "${OFFICIAL_MIRROR_BASE}/${CHECKSUM_NAME}" \
    "${NJU_MIRROR_BASE}/${CHECKSUM_NAME}"

  CHECKSUM_LINE="$(grep -E "^[[:xdigit:]]{64}[[:space:]]+\\*?${ARCHIVE_NAME}$" \
    "${DOWNLOAD_DIR}/${CHECKSUM_NAME}" | head -n 1 || true)"
  if [[ -z "${CHECKSUM_LINE}" ]]; then
    echo "Release checksum manifest does not contain ${ARCHIVE_NAME}; refusing unverified archive." >&2
    cat "${DOWNLOAD_DIR}/${CHECKSUM_NAME}" >&2
    exit 3
  fi

  fetch_first_available "${DOWNLOAD_DIR}/${ARCHIVE_NAME}" \
    "${OFFICIAL_MIRROR_BASE}/${ARCHIVE_NAME}" \
    "${OFFICIAL_BASE}/${ARCHIVE_NAME}" \
    "${NJU_MIRROR_BASE}/${ARCHIVE_NAME}"

  printf '%s\n' "${CHECKSUM_LINE}" > "${DOWNLOAD_DIR}/expected.sha256"
  (cd "${DOWNLOAD_DIR}" && sha256sum --check expected.sha256)

  tar --extract --xz --file "${DOWNLOAD_DIR}/${ARCHIVE_NAME}" \
    --directory "${INSTALL_ROOT}" --no-same-owner
fi

if [[ ! -x "${BLENDER_BIN}" ]]; then
  echo "Blender binary was not found after installation: ${BLENDER_BIN}" >&2
  exit 4
fi

VERSION_LINE="$("${BLENDER_BIN}" --version | head -n 1)"
if [[ "${VERSION_LINE}" != *"Blender ${BLENDER_VERSION}"* ]]; then
  echo "Unexpected Blender version: ${VERSION_LINE}" >&2
  exit 5
fi

echo "A-SQUARE BLENDER TOOLCHAIN READY: ${VERSION_LINE}"
export PATH="${BLENDER_DIR}:${PATH}"
if [[ -n "${GITHUB_PATH:-}" ]]; then
  echo "${BLENDER_DIR}" >> "${GITHUB_PATH}"
fi
