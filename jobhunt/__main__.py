import argparse

from .server import main

p = argparse.ArgumentParser(description="JobHuntAI web UI")
p.add_argument("--host", default="127.0.0.1")
p.add_argument("--port", type=int, default=8765)
a = p.parse_args()
main(a.host, a.port)
