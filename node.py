import socket
import threading
import json
import sys
import os
import time
import http.server
import socketserver
from core import Blockchain, Block

PORT = 5000
PEERS = ['10.0.0.1', '10.0.0.2', '10.0.0.3']

class Node:
    def __init__(self, host):
        self.host = host
        self.blockchain = Blockchain(difficulty=4) # ここの数字を大きくするとマイニングが難しくなる
        
    def start_server(self):
        """ 他ノードからの接続を待ち受けるTCPサーバー """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, PORT))
        server.listen(5)
        print(f"[*] Node Server started on {self.host}:{PORT}")
        
        while True:
            client, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()

    def handle_client(self, client):
        """ 受信したメッセージを処理する """
        try:
            # 大きなチェーンデータも受け取れるようバッファを大きめに取る
            data = client.recv(40960).decode('utf-8')
            if not data:
                return
            message = json.loads(data)
            
            msg_type = message.get('type')
            
            if msg_type == 'new_block':
                # 新しいブロックをブロードキャストで受け取った時
                block_data = message.get('block')
                new_block = Block.from_dict(block_data)
                
                latest_block = self.blockchain.get_latest_block()
                if new_block.prev_hash == latest_block.hash:
                    # ハッシュとPoWの検証
                    if new_block.hash == new_block.calculate_hash() and new_block.is_valid_pow(self.blockchain.difficulty):
                        self.blockchain.chain.append(new_block)
                        print(f"\n[+] ネットワークから新しいブロックを受信し、チェーンに追加しました！ Transaction: {new_block.transaction}")
                    else:
                        print("\n[-] 受信したブロックは不正です。")
                else:
                    print("\n[!] 受信したブロックは最新ブロックと繋がりません。チェーンの同期が必要です (コマンド: sync)。")
                    
            elif msg_type == 'request_chain':
                # 他ノードからチェーンの同期を要求された時
                response = {
                    'type': 'chain_response',
                    'chain': self.blockchain.get_chain_data()
                }
                client.send(json.dumps(response).encode('utf-8'))
                
            elif msg_type == 'chain_response':
                # チェーンの同期要求に対する応答を受け取った時
                chain_data = message.get('chain')
                success = self.blockchain.replace_chain(chain_data)
                if success:
                    print("\n[+] チェーンが同期され、より長くて正当なチェーンに置き換わりました。")
                else:
                    print("\n[-] 受信したチェーンは既存のチェーンより短いか、不正なため破棄されました。")
                    
        except Exception as e:
            print(f"\n[-] 通信エラー: {e}")
        finally:
            client.close()

    def send_message(self, target_ip, message):
        """ 指定したIPアドレスにメッセージを送信する """
        if target_ip == self.host:
            return # 自分自身には送らない
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5)  # 念のためタイムアウトを延長
            client.connect((target_ip, PORT))
            client.send(json.dumps(message).encode('utf-8'))
            
            # チェーン同期要求の場合は応答を待つ
            if message.get('type') == 'request_chain':
                data = client.recv(40960).decode('utf-8')
                if data:
                    resp = json.loads(data)
                    if resp.get('type') == 'chain_response':
                        success = self.blockchain.replace_chain(resp.get('chain'))
                        if success:
                            print(f"[+] {target_ip} からチェーンを同期しました。")
            client.close()
            print(f"[debug] メッセージ({message.get('type')})を {target_ip} に送信完了しました。")
        except Exception as e:
            print(f"[debug] {target_ip} への送信に失敗しました: {e}")

    def broadcast(self, message):
        """ ネットワーク全体（全ピア）にメッセージを送信する """
        for peer in PEERS:
            self.send_message(peer, message)

    def interactive_console(self):
        """ ユーザーからの入力を受け付ける対話コンソール """
        while True:
            cmd = input(f"\n[{self.host}] コマンドを入力 (mine <tx> / chain / sync / exit): ").strip()
            
            if cmd.startswith("mine "):
                tx = cmd[5:]
                print(f"[{tx}] を含む新しいブロックをマイニング中...")
                prev_block = self.blockchain.get_latest_block()
                new_block = Block(tx, prev_block.hash)
                new_block.mine(self.blockchain.difficulty)
                self.blockchain.chain.append(new_block)
                print(f"マイニング成功！ネットワークにブロードキャストします...")
                self.broadcast({
                    'type': 'new_block',
                    'block': new_block.to_dict()
                })
                
            elif cmd == "chain":
                chain_data = self.blockchain.get_chain_data()
                print(json.dumps(chain_data, indent=2, ensure_ascii=False))
                
            elif cmd == "sync":
                print("ネットワークにチェーンの同期を要求しています...")
                self.broadcast({'type': 'request_chain'})
                
            elif cmd == "exit":
                print("終了します...")
                os._exit(0)
                
            elif cmd:
                print("不明なコマンドです。")

    def start_web_server(self):
        """ Web UI と API を提供する HTTP サーバー """
        node_instance = self
        
        class APIHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass # アクセスログを抑制
                
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    with open('web_ui.html', 'rb') as f:
                        self.wfile.write(f.read())
                elif self.path == '/api/info':
                    response_data = json.dumps({'host': node_instance.host}).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Content-Length', str(len(response_data)))
                    self.end_headers()
                    self.wfile.write(response_data)
                elif self.path == '/api/chain':
                    response_data = json.dumps({'chain': node_instance.blockchain.get_chain_data()}).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Content-Length', str(len(response_data)))
                    self.end_headers()
                    self.wfile.write(response_data)
                else:
                    self.send_error(404)

            def do_POST(self):
                if self.path == '/api/mine':
                    try:
                        content_length = int(self.headers.get('Content-Length', 0))
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode('utf-8'))
                        tx = data.get('transaction', '')
                        
                        if tx:
                            print(f"\n[Web UI] [{tx}] を含む新しいブロックをマイニング中...")
                            prev_block = node_instance.blockchain.get_latest_block()
                            new_block = Block(tx, prev_block.hash)
                            new_block.mine(node_instance.blockchain.difficulty)
                            node_instance.blockchain.chain.append(new_block)
                            print(f"[Web UI] マイニング成功！ネットワークにブロードキャストします...")
                            node_instance.broadcast({
                                'type': 'new_block',
                                'block': new_block.to_dict()
                            })
                            response_data = json.dumps({'status': 'success', 'block': new_block.to_dict()}).encode('utf-8')
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Content-Length', str(len(response_data)))
                            self.end_headers()
                            self.wfile.write(response_data)
                        else:
                            response_data = json.dumps({'error': 'No transaction provided'}).encode('utf-8')
                            self.send_response(400)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Content-Length', str(len(response_data)))
                            self.end_headers()
                            self.wfile.write(response_data)
                    except Exception as e:
                        response_data = json.dumps({'error': str(e)}).encode('utf-8')
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Content-Length', str(len(response_data)))
                        self.end_headers()
                        self.wfile.write(response_data)
                
                elif self.path == '/api/sync':
                    print("\n[Web UI] ネットワークにチェーンの同期を要求しています...")
                    node_instance.broadcast({'type': 'request_chain'})
                    response_data = json.dumps({'status': 'sync_requested'}).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Content-Length', str(len(response_data)))
                    self.end_headers()
                    self.wfile.write(response_data)
                else:
                    self.send_error(404)

        socketserver.TCPServer.allow_reuse_address = True
        try:
            httpd = socketserver.TCPServer((self.host, 8080), APIHandler)
            print(f"[*] Web UI Server started on http://{self.host}:8080")
            httpd.serve_forever()
        except Exception as e:
            print(f"[-] Web UI サーバーの起動に失敗しました: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 node.py <ip_address>")
        sys.exit(1)
        
    host_ip = sys.argv[1]
    node = Node(host_ip)
    
    # P2Pサーバーをバックグラウンドスレッドで起動
    server_thread = threading.Thread(target=node.start_server, daemon=True)
    server_thread.start()
    
    # Webサーバーをバックグラウンドスレッドで起動
    web_thread = threading.Thread(target=node.start_web_server, daemon=True)
    web_thread.start()
    
    # サーバー起動のログが出るまで少し待つ
    time.sleep(0.5)
    
    # コンソール入力をメインスレッドで実行
    node.interactive_console()

if __name__ == "__main__":
    main()
