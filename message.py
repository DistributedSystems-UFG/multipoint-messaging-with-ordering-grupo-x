import time
from datetime import datetime, timezone


class Message:
    def __init__(self, content, author, seq_num=None):
        self.content = content
        self.author = author  # (ipaddr, port) tuple
        self.timestamp = time.time()
        self.seq_num = seq_num  # assigned by GroupManager; None until sequenced

    def __repr__(self):
        ts = datetime.fromtimestamp(self.timestamp, tz=timezone.utc).strftime("%d/%b/%Y %H:%M:%S")
        return f"[#{self.seq_num}] [{ts}] [{self.author}] {self.content}"