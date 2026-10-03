import argparse

from .server import main

p = argparse.ArgumentParser(description="JobHuntAI web UI")
p.add_argument("--host", default="127.0.0.1")
p.add_argument("--port", type=int, default=8765)
p.add_argument("--jobs-csv", action="store_true", help="print the path of the job log CSV and exit")
a = p.parse_args()
if a.jobs_csv:
    from .tracker import csv_path
    print(csv_path())
    raise SystemExit
main(a.host, a.port)
