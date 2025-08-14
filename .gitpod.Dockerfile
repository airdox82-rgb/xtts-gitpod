# .gitpod.Dockerfile — klassisch: auf workspace-full aufsetzen
FROM gitpod/workspace-full

# Optional: ffmpeg für Audio-Konvertierung (mp3 -> wav)
RUN sudo apt-get update && sudo apt-get install -y ffmpeg && sudo rm -rf /var/lib/apt/lists/*
