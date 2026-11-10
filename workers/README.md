# NOVA Studio local GPU worker

## Implemented worker pipeline
- Polls the durable NOVA Studio queue over outbound HTTPS.
- Uses ComfyUI on localhost to generate four AI scene frames from NOVA-authored visual prompts.
- Uses FFmpeg to animate the stills with cinematic camera movement and assemble a vertical, square or landscape MP4.
- Uses Swedish Edge TTS narration or optional offline Piper, time-aligned SRT subtitles and MP4 decode validation.
- Can generate the screenplay locally with Ollama (Qwen 2.5 3B) so the cloud NOVA text model is optional.
- Uploads the MP4 and SRT to the existing private nova-videos bucket.
- Reports progress, worker heartbeat and failures; a stale lease is recovered by the cloud queue.

## Requirements
- Windows 10/11, Python 3.11 or 3.12.
- ComfyUI listening on 127.0.0.1:8188.
- A compatible SD 1.5 checkpoint installed in ComfyUI. Default filename: v1-5-pruned-emaonly.safetensors.
- The Render service must have NOVA_STUDIO_WORKER_TOKEN configured with the same secret as the local machine.
- The Supabase migration must be applied to JARVIS-MEMORY.

## Start
Use start_nova_studio_windows.bat after setting the environment variables described in SETUP.md.

## Honest quality limits
This release generates four AI still frames and animates them with camera motion. It is not frame-by-frame text-to-video, does not guarantee perfectly consistent characters between scenes, and is not claimed to match Pixar. Persistent character references, motion synthesis, music/sound design and full end-to-end production QA remain future work.
