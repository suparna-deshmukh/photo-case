"""Child-process launcher for the Streamlit backend.

Run as: python -m jog_child run app.py --server.port 8901 ...
Raises the file-descriptor soft limit (Fluid Compute instances get a
low default) before importing the (FD-hungry) stack.
"""

import resource

try:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft < 1048576:
        resource.setrlimit(resource.RLIMIT_NOFILE, (max(soft, min(hard, 1048576)), hard))
except Exception:  # noqa: BLE001
    pass

from streamlit.web.cli import main

if __name__ == "__main__":
    main(prog_name="streamlit")
