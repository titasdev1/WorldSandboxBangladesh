#!/usr/bin/env bash
set -euo pipefail

# Reproducible authoring toolchain for the A-Square asset pipeline.
# Use the supported LTS line, not the Ubuntu runner's potentially older apt package.
BLENDER_VERSION="${BLENDER_VERSION:-5.2.4}"
BLENDER_SERIES="Blender5.2"
ARCHIVE_NAME="blender-${BLENDER_VERSION}-linux-x64.tar.xz"
BASE_URL="https://download.blender.org/release/${BLENDER_SERIES}"
RUNNER_TEMP_DIR="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
INSTALL_ROOT="${BLENDER_INSTALL_ROOT:-${RUNNER_TEMP_DIR}/blender-${BLENDER_VERSION}}"
BLENDER_DIR="${INSTALL_ROOT}/blender-${BLENDER_VERSION}-linux-x64"
BLENDER_BIN="${BLENDER_DIR}/blender"

if [[ "${BLENDER_VERSION}" != "5.2.4" ]]; then
  echo "This project currently validates Blender 5.2.4 LTS; refusing an unreviewed version: ${BLENDER_VERSION}" >&2
  exit 2
fi

if [[ ! -x "${BLENDER_BIN}" ]]; then
  mkdir -p "${INSTALL_ROOT}"
  DOWNLOAD_DIR="$(mktemp -d "${RUNNER_TEMP_DIR}/blender-download.XXXXXX")"
  trap 'rm -rf "${DOWNLOAD_DIR}"' EXIT

  curl --fail --location --retry 3 --retry-delay 2 \
    "${BASE_URL}/${ARCHIVE_NAME}" -o "${DOWNLOAD_DIR}/${ARCHIVE_NAME}"
  curl --fail --location --retry 3 --retry-delay 2 \
    "${BASE_URL}/blender-${BLENDER_VERSION}.sha256" -o "${DOWNLOAD_DIR}/blender-${BLENDER_VERSION}.sha256"

  CHECKSUM_LINE="$(grep -E "^[[:xdigit:]]{64}[[:space:]]+\\*?${ARCHIVE_NAME}$" \
    "${DOWNLOAD_DIR}/blender-${BLENDER_VERSION}.sha256" | head -n 1 || true)"
  if [[ -z "${CHECKSUM_LINE}" ]]; then
    echo "Official Blender checksum manifest does not contain ${ARCHIVE_NAME}; refusing unverified archive." >&2
    cat "${DOWNLOAD_DIR}/blender-${BLENDER_VERSION}.sha256" >&2
    exit 3
  fi
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
if [[ -n "${GITHUB_PATH:-}" ]]; then
  echo "${BLENDER_DIR}" >> "${GITHUB_PATH}"
fi
