#!/bin/bash

# Run migration inside the Docker container
docker exec clarity-local_api bash -c "cd /app && alembic upgrade head"