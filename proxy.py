import socket
import threading
import sys
import subprocess
import time

def setup_bridge_ip():
    """ 仮想ブリッジにホスト側からアクセスできるようにIPを設定する """
    print("[*] Setting up IP for br0 to enable routing...")
    try:
        # すでに設定されているか確認
        out = subprocess.check_output("ip addr show br0", shell=True).decode()
        if "10.0.0.254" not in out:
            subprocess.run("sudo ip addr add 10.0.0.254/24 dev br0", shell=True, check=True)
            print("[+] Added 10.0.0.254 to br0")
    except Exception as e:
        print(f"[-] Failed to setup br0 IP: {e}")
        print("Please run manually: sudo ip addr add 10.0.0.254/24 dev br0")

def forward(source, destination):
    """ 双方向にデータを転送する """
    try:
        while True:
            data = source.recv(4096)
            if len(data) == 0:
                break
            destination.sendall(data)
    except Exception:
        pass
    finally:
        source.close()
        destination.close()

def handle_client(client_socket, target_ip, target_port):
    """ クライアントの接続をターゲットにフォワードする """
    target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        target_socket.connect((target_ip, target_port))
    except Exception as e:
        print(f"[-] Failed to connect to {target_ip}:{target_port} - {e}")
        client_socket.close()
        return

    # 双方向のフォワーディングスレッドを開始
    threading.Thread(target=forward, args=(client_socket, target_socket), daemon=True).start()
    threading.Thread(target=forward, args=(target_socket, client_socket), daemon=True).start()

def start_proxy(local_port, target_ip, target_port):
    """ ローカルポートの待ち受けを開始する """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', local_port))
        server.listen(5)
        print(f"[*] Proxy running: Windows http://localhost:{local_port} -> {target_ip}:{target_port}")
    except Exception as e:
        print(f"[-] Failed to bind port {local_port}: {e}")
        return

    while True:
        try:
            client, addr = server.accept()
            threading.Thread(target=handle_client, args=(client, target_ip, target_port), daemon=True).start()
        except KeyboardInterrupt:
            break

def main():
    print("=== WSL Web UI Port Forwarder ===")
    setup_bridge_ip()
    
    proxies = [
        (8081, '10.0.0.1', 8080),
        (8082, '10.0.0.2', 8080),
        (8083, '10.0.0.3', 8080),
    ]

    threads = []
    for local_port, target_ip, target_port in proxies:
        t = threading.Thread(target=start_proxy, args=(local_port, target_ip, target_port), daemon=True)
        t.start()
        threads.append(t)

    print("[*] All proxies started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping proxies...")
        sys.exit(0)

if __name__ == '__main__':
    main()
