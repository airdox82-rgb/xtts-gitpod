FROM gitpod/workspace-full

# Add custom tools and dependencies
# Install system dependencies for the voice cloner GUI application.
# PortAudio is required by the 'sounddevice' Python library for audio I/O.
USER root
RUN apt-get update && apt-get install -y libportaudio2 portaudio19-dev libxcb-cursor0 &&     rm -rf /var/lib/apt/lists/*
USER gitpod
