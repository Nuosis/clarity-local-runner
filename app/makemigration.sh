#!/bin/bash

read -p "Enter the migration message: " user_input

escaped_input=$(echo $user_input | sed 's/"/\\"/g')

# Run migration generation inside the Docker container
docker exec clarity-local_api bash -c "cd /app && alembic revision --autogenerate -m \"$escaped_input\""