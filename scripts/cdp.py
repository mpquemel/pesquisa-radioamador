import json, socket, base64, struct, os, sys
from urllib.request import urlopen

class CDP:
    def __init__(self, ws_url):
        # ws_url: ws://127.0.0.1:9222/devtools/page/XXX
        rest = ws_url.split("://",1)[1]
        hostport, path = rest.split("/",1)
        self.path = "/" + path
        h,p = hostport.split(":")
        self.s = socket.create_connection((h,int(p)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = f"GET {self.path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        self.s.sendall(req.encode())
        buf=b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        assert b"101" in buf.split(b"\r\n")[0], buf[:200]
        self.buf = buf.split(b"\r\n\r\n",1)[1]
        self.mid = 0
    def _recv(self, n):
        while len(self.buf) < n:
            d = self.s.recv(65536)
            if not d: raise EOFError
            self.buf += d
        out, self.buf = self.buf[:n], self.buf[n:]
        return out
    def _read_frame(self):
        b1,b2 = self._recv(2)
        ln = b2 & 0x7f
        if ln == 126: ln = struct.unpack(">H", self._recv(2))[0]
        elif ln == 127: ln = struct.unpack(">Q", self._recv(8))[0]
        mask = None
        if b2 & 0x80: mask = self._recv(4)
        data = self._recv(ln)
        if mask:
            data = bytes(c ^ mask[i%4] for i,c in enumerate(data))
        return b1 & 0x0f, data
    def send(self, payload):
        data = json.dumps(payload).encode()
        mask = os.urandom(4)
        masked = bytes(c ^ mask[i%4] for i,c in enumerate(data))
        header = bytes([0x81])
        n = len(data)
        if n < 126: header += bytes([0x80|n])
        elif n < 65536: header += bytes([0x80|126]) + struct.pack(">H", n)
        else: header += bytes([0x80|127]) + struct.pack(">Q", n)
        self.s.sendall(header + mask + masked)
    def recv_all(self):
        while True:
            op, data = self._read_frame()
            if op == 1:
                return json.loads(data)
    def call(self, method, params=None, timeout=None):
        self.mid += 1
        mid = self.mid
        self.send({"id": mid, "method": method, "params": params or {}})
        while True:
            msg = self.recv_all()
            if msg.get("id") == mid:
                if "error" in msg: raise RuntimeError(msg["error"])
                return msg.get("result", {})
    def eval(self, expr, awaitPromise=False):
        r = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": awaitPromise})
        return r.get("result", {}).get("value"), r.get("exceptionDetails")
