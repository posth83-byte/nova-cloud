# Windows + NVIDIA setup for NOVA Studio

This worker uses the local ComfyUI API. The image model runs on the PC, not on Render.

## 1. Install ComfyUI

For an NVIDIA RTX 20-series card such as the RTX 2060, use the official Windows portable NVIDIA build:
https://github.com/Comfy-Org/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z

Extract it, then start ComfyUI with run_nvidia_gpu.bat. Keep its console window open. The default local API is http://127.0.0.1:8188.

Official installation guide: https://docs.comfy.org/installation/comfyui_portable_windows

## 2. Install the checkpoint

Download the FP16 Stable Diffusion 1.5 checkpoint:
https://huggingface.co/Comfy-Org/stable-diffusion-1.5/resolve/main/v1-5-pruned-emaonly-fp16.safetensors

Put it in:
ComfyUI/models/checkpoints/

The worker's default checkpoint name is v1-5-pruned-emaonly-fp16.safetensors. If you use a different filename, set COMFYUI_CHECKPOINT to match it exactly.

The checkpoint is under the CreativeML OpenRAIL-M licence. Read the model card and licence before using or redistributing generated content:
https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5

## 3. Start the NOVA worker

1. Configure NOVA_STUDIO_URL and NOVA_STUDIO_WORKER_TOKEN in Windows environment variables.
2. Optional: configure PIPER_MODEL for fully offline Swedish TTS; see LOCAL_VOICE.md.
3. Run workers/start_nova_studio_windows.bat from the repository.

The worker contacts only the NOVA Cloud HTTPS API and ComfyUI on localhost. Do not expose ComfyUI to the public internet or add --listen 0.0.0.0.
