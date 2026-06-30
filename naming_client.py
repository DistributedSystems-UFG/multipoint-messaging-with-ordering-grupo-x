import zmq
from const_mp import NAMING_SERVICE_ADDR, NAMING_SERVICE_PORT


class NamingClient:
    def __init__(self, addr=NAMING_SERVICE_ADDR, port=NAMING_SERVICE_PORT):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f'tcp://{addr}:{port}')

    def _send(self, req):
        self.socket.send_json(req)
        return self.socket.recv_json()

    def bind(self, name, address):
        return self._send({"op": "bind", "name": name, "address": address})

    def lookup(self, name):
        return self._send({"op": "lookup", "name": name})

    def unbind(self, name):
        return self._send({"op": "unbind", "name": name})

    def register(self, name, type_):
        return self._send({"op": "register", "name": name, "type": type_})

    def discover(self, type_):
        return self._send({"op": "discover", "type": type_})
