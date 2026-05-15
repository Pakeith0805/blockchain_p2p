#!/bin/bash
# test_netns.sh - Tests connectivity between the network namespaces

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "Testing connectivity from node1 to other nodes..."

echo "--- Pinging node2 (10.0.0.2) from node1 ---"
ip netns exec node1 ping -c 3 10.0.0.2

echo ""
echo "--- Pinging node3 (10.0.0.3) from node1 ---"
ip netns exec node1 ping -c 3 10.0.0.3

echo ""
echo "Connectivity test finished."
