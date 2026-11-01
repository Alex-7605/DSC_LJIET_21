"""Convenient local launcher that leaves occupied ports and other applications alone."""
from pathlib import Path
import argparse
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parents[1]

def available_port(ports=range(8501,8511)):
    for port in ports:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1",port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free local port between 8501 and 8510. Close an unused project window or run Streamlit with another port.")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--no-browser",action="store_true")
    args=parser.parse_args()
    port=available_port()
    command=[sys.executable,"-m","streamlit","run",str(ROOT/"app.py"),"--server.address","127.0.0.1","--server.port",str(port)]
    print(f"SupplyLens: http://127.0.0.1:{port}",flush=True)
    child=subprocess.Popen(command,cwd=ROOT)
    try:
        if not args.no_browser:
            for _ in range(40):
                if child.poll() is not None:
                    raise RuntimeError("The app stopped during startup. Read the message above.")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health",timeout=.5) as response:
                        if response.status==200:
                            webbrowser.open(f"http://127.0.0.1:{port}")
                            break
                except OSError:
                    time.sleep(.25)
        return child.wait()
    except KeyboardInterrupt:
        child.terminate()
        return child.wait(timeout=10)

if __name__=="__main__":
    try:
        sys.exit(main())
    except (RuntimeError,OSError) as error:
        print(str(error),file=sys.stderr)
        sys.exit(1)
