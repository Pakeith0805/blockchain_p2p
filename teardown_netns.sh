#!/bin/bash
# teardown_netns.sh - Cleans up the virtual network environment

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "Tearing down virtual network..."

for i in {1..3}
do
  NODE="node$i"
  echo "Deleting namespace $NODE (and associated veth interfaces)..."
  ip netns delete $NODE 2>/dev/null || true
done

echo "Deleting bridge br0..."
ip link delete br0 type bridge 2>/dev/null || true

echo "Teardown complete."
