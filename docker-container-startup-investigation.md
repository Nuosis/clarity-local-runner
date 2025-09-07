# Docker Container Startup Investigation

## Symptom
Docker container for Cedar Heights backend fails to start due to two main issues:
1. Supabase client initialization fails with 'supabase_key is required' error
2. Database connection fails trying to connect to localhost:5432 instead of the Supabase database within the Docker network

## Steps to Recreate
1. Build Docker image with updated dependencies (pyjwt, supabase)
2. Run container with environment variables: `docker run -d --name cedar-heights-backend_api --network cedar-heights-backend_network --env-file docker/.env -e SUPABASE_URL=http://localhost:8000 -e SUPABASE_KEY=<service_role_key> -e DATABASE_URL=postgresql://postgres:password@supabase-db:5432/postgres -p 127.0.0.1:8080:8080 docker-api:latest`
3. Check logs with `docker logs cedar-heights-backend_api`

## Attempts to Solve the Problem
1. Verified JWT dependencies are installed in Docker image
2. Attempted to pass environment variables via --env-file and -e flags
3. Used correct Docker network (cedar-heights-backend_network)
4. Verified Supabase services are running in Docker network
5. Used service role key from docker/.env file
6. Attempted to use supabase-db hostname for database connection

## Hypotheses

1. **Environment Variable Passing** (Most Fundamental)
   - hypothesis: Environment variables are not being properly passed to the Docker container
   - null hypothesis: Environment variables are correctly passed and accessible within the container

2. **Docker Network Connectivity**
   - hypothesis: Container cannot reach Supabase services within the Docker network
   - null hypothesis: Container can properly communicate with Supabase services on the Docker network

3. **Supabase URL Format**
   - hypothesis: SUPABASE_URL format is incorrect for container-to-container communication
   - null hypothesis: SUPABASE_URL format is correct for Docker network communication

4. **Environment Variable Names**
   - hypothesis: Application expects different environment variable names than what's being provided
   - null hypothesis: Environment variable names match what the application expects

5. **Database Connection String**
   - hypothesis: DATABASE_URL format is incorrect for Supabase database connection
   - null hypothesis: DATABASE_URL format is correct for connecting to Supabase database

6. **Application Configuration Loading** (Most Dependent)
   - hypothesis: Application configuration loading mechanism fails to read environment variables
   - null hypothesis: Application configuration loading works correctly and reads environment variables