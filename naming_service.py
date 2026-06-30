import zmq
from const_mp import NAMING_SERVICE_PORT


class NamingService:
    def __init__(self, port=NAMING_SERVICE_PORT):
        self.port = port
        self.registry = {}  # name -> address
        self.types = {}     # name -> type
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f'tcp://*:{port}')

    def _bind(self, name, address):
        self.registry[name] = address
        return {"status": "ok"}

    def _lookup(self, name):
        if name in self.registry:
            return {"address": self.registry[name]}
        return {"error": f"name not found: {name}"}

    def _unbind(self, name):
        if name not in self.registry:
            return {"error": f"name not found: {name}"}
        del self.registry[name]
        self.types.pop(name, None)
        return {"status": "ok"}

    def _register(self, name, type_):
        if name not in self.registry:
            return {"error": f"name not found: {name}"}
        self.types[name] = type_
        return {"status": "ok"}

    def _discover(self, type_):
        result = [
            {"name": name, "address": self.registry[name]}
            for name, t in self.types.items()
            if t == type_
        ]
        return {"result": result}

    def run(self):
        handlers = {
            "bind":     lambda r: self._bind(r["name"], r["address"]),
            "lookup":   lambda r: self._lookup(r["name"]),
            "unbind":   lambda r: self._unbind(r["name"]),
            "register": lambda r: self._register(r["name"], r["type"]),
            "discover": lambda r: self._discover(r["type"]),
        }
        print(f'NamingService listening on port {self.port}...')
        while True:
            msg = self.socket.recv_json()
            op = msg.get("op")
            handler = handlers.get(op)
            if handler:
                reply = handler(msg)
            else:
                reply = {"error": f"unknown op: {op}"}
            self.socket.send_json(reply)


if __name__ == '__main__':
    ns = NamingService()
    ns.run()
