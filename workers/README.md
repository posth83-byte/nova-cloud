# NOVA Studio local GPU worker

## Implemented in this branch
- Cloud job creation and status endpoints.
- Durable Postgres queue with atomic claim and stale-lease recovery.
- Worker-only bearer-token authentication.
- Private MP4/SRT upload endpoint with size and MP4 signature validation.
- Windows worker bootstrap checking ComfyUI on localhost and polling the cloud.

## Not yet production-ready
The worker deliberately does not claim to render yet. The ComfyUI workflow adapter, scene/storyboard generation, audio assembly, artifact retrieval verification, and Windows installer remain outstanding. No job is marked completed by the bootstrap worker.

## Server setup
1. Apply the migration in supabase/migrations/202611100001_nova_studio_jobs.sql to JARVIS-MEMORY.
2. Set NOVA_STUDIO_WORKER_TOKEN in Render to a long random secret.
3. Confirm the existing private nova-videos bucket permits service-role uploads.
4. Deploy only after CI passes.

## Windows setup
Install ComfyUI and a model whose license permits your intended use. Set NOVA_STUDIO_URL, NOVA_STUDIO_WORKER_TOKEN, and optionally COMFYUI_URL, then run python workers/nova_studio_worker.py. Keep the PC powered on for local generation.
