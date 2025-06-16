#!/bin/bash

# Install system dependencies
apt-get update
apt-get install -y ffmpeg

# Start the application
exec python app.py