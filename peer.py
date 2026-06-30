from socket import *
import os
import pickle
from naming_client import NamingClient

PEER_UDP_PORT = 6789


def _get_local_ip():
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


class Peer:
    def __init__(self, port=PEER_UDP_PORT):
        self.port = port
        self.ipaddr = os.environ.get('MP_IP') or _get_local_ip()
        self.name = f'peer_{self.ipaddr}_{self.port}'
        self.naming = NamingClient()
        self.group = self._lookup_group_manager()
        self.recv_socket = socket(AF_INET, SOCK_DGRAM)
        self.recv_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.recv_socket.bind(('0.0.0.0', self.port))
        self.next_expected = 1
        self.hold_back = {}

    def _lookup_group_manager(self):
        reply = self.naming.lookup("group_manager")
        if "error" in reply:
            raise RuntimeError(f"GroupManager not found in naming service: {reply['error']}")
        address = reply["address"]
        ip, port_str = address.rsplit(":", 1)
        return (ip, int(port_str))

    def send(self, req):
        conn = socket(AF_INET, SOCK_STREAM)
        conn.connect(self.group)
        conn.send(pickle.dumps(req))
        conn.close()

    def receive(self):
        data, _ = self.recv_socket.recvfrom(65535)
        response = pickle.loads(data)
        if isinstance(response, list):
            for msg in sorted(response, key=lambda m: m.seq_num):
                print(msg)
                self.next_expected = msg.seq_num + 1
        else:
            self.hold_back[response.seq_num] = response
            while self.next_expected in self.hold_back:
                msg = self.hold_back.pop(self.next_expected)
                print(msg)
                self.next_expected += 1

    def register(self):
        address = f'{self.ipaddr}:{self.port}'
        self.naming.bind(self.name, address)
        self.naming.register(self.name, "peer")

    def unregister(self):
        self.naming.unbind(self.name)

    def history(self):
        req = {"op": "history", "ipaddr": self.ipaddr, "port": self.port}
        self.send(req)

    def message(self, content):
        req = {"op": "message", "ipaddr": self.ipaddr, "port": self.port, "content": content}
        self.send(req)

    def stop(self):
        req = {"op": "stop"}
        self.send(req)


if __name__ == '__main__':
    import threading

    port = int(os.environ.get('MP_PORT', PEER_UDP_PORT))
    peer = Peer(port=port)
    peer.register()
    print(f"Registered as {peer.name} ({peer.ipaddr}:{peer.port})")

    def receive_loop():
        while True:
            try:
                peer.receive()
            except Exception as e:
                print(f"[receive error] {e}")
                break

    t = threading.Thread(target=receive_loop, daemon=True)
    t.start()
    peer.history()
    try:
        while True:
            content = input()
            if content:
                peer.message(content)
    except KeyboardInterrupt:
        pass
    finally:
        peer.unregister()
        print("Unregistered. Bye.")
