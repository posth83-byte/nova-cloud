# NOVA Studio Windows GPU worker

1. Install Python 3.11 or 3.12.
2. Install ComfyUI locally and launch it on http://127.0.0.1:8188.
3. Install a compatible SD 1.5 checkpoint into ComfyUI/models/checkpoints. Set COMFYUI_CHECKPOINT to the exact filename.
4. In PowerShell set NOVA_STUDIO_URL, NOVA_STUDIO_WORKER_TOKEN, and optionally COMFYUI_URL and COMFYUI_CHECKPOINT.
5. From the repository root run: pip install -r workers/requirements.txt
6. Run: python workers/nova_studio_worker.py

The worker makes outbound calls to NOVA Cloud and local calls to ComfyUI only. Keep the PC powered on during generation. The first release generates four AI stills and animates them with camera movement, adds Swedish narration and SRT subtitles, and uploads a private MP4. It is not frame-by-frame AI video or a guarantee of consistent characters across shots. Model license and available GPU memory must be checked locally.


## Optional offline Swedish voice
For fully local TTS, install Piper with `pip install piper-tts`, download the Swedish Alma medium ONNX model and matching JSON file, then set `PIPER_MODEL` to the ONNX file path. See LOCAL_VOICE.md for the direct model links and CC BY 4.0 attribution. If PIPER_MODEL is empty, the worker uses the online Edge TTS voice configured by NOVA_STUDIO_VOICE.
