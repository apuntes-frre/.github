# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
import os

if os.environ.get("PAT_TOKEN"):
    print("token detected")
else:
    print("no token")
