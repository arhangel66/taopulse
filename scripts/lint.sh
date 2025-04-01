#!/bin/bash

# Format code with black
echo "Running black..."
black .

# Check code with flake8
echo "Running flake8..."
flake8 .

echo "Linting completed!"
