import http.server
import socketserver
import json
import threading
import queue
import time

PORT = 8000

class ClientConnection:
    def __init__(self):
        self.queue = queue.Queue()

clients = []
clients_lock = threading.Lock()

def broadcast_message(message):
    with clients_lock:
        for client in clients:
            client.queue.put(message)

class RelayHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # アクセスログを抑制

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            try:
                with open('index.html', 'rb') as f:
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.wfile.write(b"index.html not found")
                
        elif self.path == '/events':
            # SSE (Server-Sent Events) ストリームの開始
            self.send_response(200)
            self.send_header('Content-type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            client = ClientConnection()
            with clients_lock:
                clients.append(client)
            
            print(f"[+] Node connected. Active nodes: {len(clients)}")
            
            try:
                # 接続確立のための初期メッセージ
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                
                while True:
                    # キューからメッセージを取得して送信
                    msg = client.queue.get()
                    if msg is None:
                        break
                    
                    response = f"data: {json.dumps(msg)}\n\n"
                    self.wfile.write(response.encode('utf-8'))
                    self.wfile.flush()
            except Exception as e:
                # クライアントが切断した場合（タブを閉じたなど）
                pass
            finally:
                with clients_lock:
                    if client in clients:
                        clients.remove(client)
                print(f"[-] Node disconnected. Active nodes: {len(clients)}")
                
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/broadcast':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                message = json.loads(post_data.decode('utf-8'))
                
                # すべての接続済みノードにメッセージをブロードキャスト
                broadcast_message(message)
                
                response_data = json.dumps({'status': 'success'}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Content-Length', str(len(response_data)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response_data)
            except Exception as e:
                response_data = json.dumps({'error': str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Content-Length', str(len(response_data)))
                self.end_headers()
                self.wfile.write(response_data)
        else:
            self.send_error(404)
            
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True

if __name__ == '__main__':
    print("=== P2P Relay Server ===")
    print(f"[*] Starting server on http://localhost:{PORT}")
    server = ThreadedHTTPServer(('0.0.0.0', PORT), RelayHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        server.server_close()
