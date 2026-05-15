#!/bin/bash
# setup_netns.sh - Sets up the virtual network environment for P2P blockchain

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

echo "Creating bridge br0..."
ip link add br0 type bridge
ip link set br0 up

for i in {1..3}
do
  NODE="node$i"
  VETH="veth$i"
  VETH_BR="${VETH}-br"
  IP="10.0.0.$i"

  echo "Setting up $NODE..."

  # Create network namespace
  ip netns add $NODE

  # Create veth pair
  ip link add $VETH type veth peer name $VETH_BR

  # Attach one end to the bridge
  ip link set $VETH_BR master br0
  ip link set $VETH_BR up

  # Move the other end to the namespace
  ip link set $VETH netns $NODE

  # Configure IP and bring up loopback and veth in namespace
  ip -n $NODE addr add $IP/24 dev $VETH
  ip -n $NODE link set $VETH up
  ip -n $NODE link set lo up
done

echo "Network namespace setup complete."
ip netns list
