#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# migrate-to-apacer.sh
#
# Partition, format, and populate the Apacer AS350 1TB (/dev/sdc):
#
#   sdc1  100 GiB   axon-server-os   (future Ubuntu Server install)
#   sdc2  600 GiB   axon-data        (Axon repos — frontend + control plane)
#   sdc3  ~253 GiB  nvme-data        (everything else from /home/edp)
#
# Run as root:  sudo bash scripts/migrate-to-apacer.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

DEVICE="/dev/sdc"
MOUNT_AXON="/mnt/axon-data"
MOUNT_NVME="/mnt/nvme-data"
HOME_DIR="/home/edp"

RED='\033[0;31m'; YEL='\033[1;33m'; GRN='\033[0;32m'; NC='\033[0m'
log()  { echo -e "${GRN}[migrate]${NC} $*"; }
warn() { echo -e "${YEL}[warn]${NC} $*"; }
die()  { echo -e "${RED}[error]${NC} $*" >&2; exit 1; }

# ── Safety checks ─────────────────────────────────────────────────────────────
[[ $EUID -eq 0 ]] || die "Run with sudo: sudo bash $0"
[[ -b "$DEVICE" ]] || die "$DEVICE not found — is the Apacer plugged in?"

warn "This will WIPE all data on $DEVICE (Apacer AS350 1TB)."
warn "sdb2 (/srv/axon-server) is NOT touched."
echo ""
read -r -p "Type YES to continue: " confirm
[[ "$confirm" == "YES" ]] || { echo "Aborted."; exit 0; }

# ── Unmount anything on sdc ──────────────────────────────────────────────────
log "Unmounting any existing sdc partitions..."
umount "${DEVICE}"* 2>/dev/null || true
sleep 1

# ── Partition ─────────────────────────────────────────────────────────────────
log "Creating GPT partition table on $DEVICE..."
parted "$DEVICE" --script -- \
  mklabel gpt \
  mkpart axon-server-os  ext4   1MiB   100GiB \
  mkpart axon-data       ext4  100GiB  700GiB \
  mkpart nvme-data       ext4  700GiB  100%

partprobe "$DEVICE"
sleep 2

log "Partition layout:"
parted "$DEVICE" print

# ── Format ────────────────────────────────────────────────────────────────────
log "Formatting sdc1 as ext4 (axon-server-os)..."
mkfs.ext4 -L axon-server-os -F "${DEVICE}1"

log "Formatting sdc2 as ext4 (axon-data, 600 GiB)..."
mkfs.ext4 -L axon-data -F "${DEVICE}2"

log "Formatting sdc3 as ext4 (nvme-data, ~253 GiB)..."
mkfs.ext4 -L nvme-data -F "${DEVICE}3"

# ── Mount ─────────────────────────────────────────────────────────────────────
log "Mounting partitions..."
mkdir -p "$MOUNT_AXON" "$MOUNT_NVME"
mount "${DEVICE}2" "$MOUNT_AXON"
mount "${DEVICE}3" "$MOUNT_NVME"

# ── Create directory structure ───────────────────────────────────────────────
log "Creating directory skeleton on axon-data..."
mkdir -p \
  "${MOUNT_AXON}/repos" \
  "${MOUNT_AXON}/projectx"

log "Creating directory skeleton on nvme-data..."
mkdir -p \
  "${MOUNT_NVME}/home" \
  "${MOUNT_NVME}/home/edp"

# ── rsync Axon repos → axon-data (sdc2) ─────────────────────────────────────
log "Syncing /home/edp/axon-nvme/ → ${MOUNT_AXON}/repos/axon-nvme ..."
rsync -aHAXv --progress \
  "${HOME_DIR}/axon-nvme/" \
  "${MOUNT_AXON}/repos/axon-nvme/"

log "Syncing /home/edp/Projectx/ → ${MOUNT_AXON}/projectx ..."
rsync -aHAXv --progress \
  "${HOME_DIR}/Projectx/" \
  "${MOUNT_AXON}/projectx/"

# ── rsync everything else → nvme-data (sdc3) ────────────────────────────────
log "Syncing /home/edp/ → ${MOUNT_NVME}/home/edp/ (excluding .cache, axon-nvme, Projectx)..."
rsync -aHAXv --progress \
  --exclude='.cache/' \
  --exclude='axon-nvme/' \
  --exclude='Projectx/' \
  "${HOME_DIR}/" \
  "${MOUNT_NVME}/home/edp/"

# ── Set ownership ─────────────────────────────────────────────────────────────
log "Setting ownership on synced data..."
chown -R edp:edp "${MOUNT_NVME}/home/edp/"
chown -R edp:edp "${MOUNT_AXON}/repos/"
chown -R edp:edp "${MOUNT_AXON}/projectx/"

# ── Write fstab entries ───────────────────────────────────────────────────────
log "Reading partition UUIDs..."
UUID_SDC2=$(blkid -s UUID -o value "${DEVICE}2")
UUID_SDC3=$(blkid -s UUID -o value "${DEVICE}3")

log "UUID axon-data:  $UUID_SDC2"
log "UUID nvme-data:  $UUID_SDC3"

FSTAB_ENTRY_2="UUID=${UUID_SDC2}  ${MOUNT_AXON}  ext4  defaults,nofail  0  2"
FSTAB_ENTRY_3="UUID=${UUID_SDC3}  ${MOUNT_NVME}  ext4  defaults,nofail  0  2"

# Back up fstab first
cp /etc/fstab /etc/fstab.bak.$(date +%Y%m%d%H%M%S)

# Remove any stale sdc entries then append
grep -v "axon-data\|nvme-data\|${UUID_SDC2}\|${UUID_SDC3}" /etc/fstab > /tmp/fstab.new
echo "" >> /tmp/fstab.new
echo "# Apacer AS350 1TB — added by migrate-to-apacer.sh" >> /tmp/fstab.new
echo "$FSTAB_ENTRY_2" >> /tmp/fstab.new
echo "$FSTAB_ENTRY_3" >> /tmp/fstab.new
mv /tmp/fstab.new /etc/fstab

log "fstab updated. Entries added:"
grep "axon-data\|nvme-data" /etc/fstab

# ── Symlinks so existing paths still resolve ─────────────────────────────────
log "Creating convenience symlinks..."

# /home/edp/axon-nvme → /mnt/axon-data/repos/axon-nvme
if [[ ! -L "${HOME_DIR}/axon-nvme" ]]; then
  mv "${HOME_DIR}/axon-nvme" "${HOME_DIR}/axon-nvme.bak.$(date +%Y%m%d%H%M%S)"
fi
ln -sfn "${MOUNT_AXON}/repos/axon-nvme" "${HOME_DIR}/axon-nvme"
chown -h edp:edp "${HOME_DIR}/axon-nvme"

# /home/edp/Projectx → /mnt/axon-data/projectx
if [[ ! -L "${HOME_DIR}/Projectx" ]]; then
  mv "${HOME_DIR}/Projectx" "${HOME_DIR}/Projectx.bak.$(date +%Y%m%d%H%M%S)"
fi
ln -sfn "${MOUNT_AXON}/projectx" "${HOME_DIR}/Projectx"
chown -h edp:edp "${HOME_DIR}/Projectx"

# ── Verify ────────────────────────────────────────────────────────────────────
log "Done. Final mount state:"
df -h "${DEVICE}2" "${DEVICE}3"
echo ""
log "Symlinks:"
ls -la "${HOME_DIR}/axon-nvme" "${HOME_DIR}/Projectx"
echo ""
log "Axon-data contents:"
ls "${MOUNT_AXON}/repos/"
echo ""
warn "sdb2 (/srv/axon-server) was NOT touched — it stays exactly as-is."
warn ""
warn "After Kali reinstall on the NVMe:"
warn "  1. Mount sdc2 (UUID=$UUID_SDC2) at ${MOUNT_AXON}"
warn "  2. Mount sdc3 (UUID=$UUID_SDC3) at ${MOUNT_NVME}"
warn "  3. Restore home from ${MOUNT_NVME}/home/edp/"
warn "  4. Re-create symlinks for axon-nvme and Projectx"
warn ""
log "Migration complete."
