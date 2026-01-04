# How we run bot locally
docker run --env-file .env -v "$(pwd)/sessions/pool_{k}:/app/sessions:ro" ai-assistant:v1.0.release 