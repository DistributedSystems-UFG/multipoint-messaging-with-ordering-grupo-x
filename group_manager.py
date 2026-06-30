from socket import *
import pickle
from message import Message
from naming_client import NamingClient

GROUPMNGR_TCP_PORT = 5680


def _get_local_ip():
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


class GroupManager:
    def __init__(self, port=GROUPMNGR_TCP_PORT):
        self.port = port
        self.ipaddr = _get_local_ip()
        self.messages = []
        self.seq_counter = 0
        self.naming = NamingClient()
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.listen(6)
        self._register_self()

    def _register_self(self):
        address = f'{self.ipaddr}:{self.port}'
        self.naming.bind("group_manager", address)
        self.naming.register("group_manager", "group_manager")
        print(f'Registered in naming service as group_manager at {address}')

    def _get_peers(self):
        reply = self.naming.discover("peer")
        return reply.get("result", [])

    def __op_history(self, req, conn):
        sorted_messages = sorted(self.messages, key=lambda m: m.seq_num)
        payload = pickle.dumps(sorted_messages)
        sock = socket(AF_INET, SOCK_DGRAM)
        sock.sendto(payload, (req.get("ipaddr"), req.get("port")))
        sock.close()

    def __op_message(self, req, conn):
        self.seq_counter += 1
        author = (req.get("ipaddr"), req.get("port"))
        msg = Message(content=req.get("content"), author=author, seq_num=self.seq_counter)
        print(f'Message received: {msg}')
        self.messages.append(msg)
        payload = pickle.dumps(msg)
        sock = socket(AF_INET, SOCK_DGRAM)
        for peer in self._get_peers():
            ip, port_str = peer["address"].rsplit(":", 1)
            sock.sendto(payload, (ip, int(port_str)))
            print(f'Forwarded message to {peer["name"]} ({peer["address"]})')
        sock.close()

    def __op_stop(self, req, conn):
        print("Stopping.")
        self.naming.unbind("group_manager")
        self.socket.close()
        return False

    def run(self):
        handlers = {
            "history": self.__op_history,
            "message": self.__op_message,
            "stop":    self.__op_stop,
        }
        print(f'GroupManager listening on {self.ipaddr}:{self.port}...')
        while True:
            (conn, addr) = self.socket.accept()
            try:
                msgPack = conn.recv(2048)
                req = pickle.loads(msgPack)
                op = req.get("op")
                handler = handlers.get(op)
                if handler:
                    if handler(req, conn) is False:
                        break
                else:
                    print('Unknown operation:', op)
                    conn.send(pickle.dumps({"error": f"unknown op: {op}"}))
            finally:
                conn.close()


if __name__ == '__main__':
    gm = GroupManager()
    gm.run()
