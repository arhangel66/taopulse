#!/bin/bash

# Set environment variables to help with Python multiprocessing in Docker
export PYTHONUNBUFFERED=1
export PYTHONFAULTHANDLER=1

# Disable multiprocessing logging to avoid EOFError
export PYTHONMULTIPROCESSING=1

# Execute the command passed to the script
exec "$@"
