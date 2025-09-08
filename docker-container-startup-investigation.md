# Docker Container Startup Investigation

## Symptom
Docker containers start successfully until analytics container, but then API container fails to start with error: 'exec: "./app/start.sh": stat ./app/start.sh: no such file or directory: unknown'. We know this because:
- supabase-studio and supabase-storage containers are created successfully
- Analytics container appears to run correctly after some time
- API container fails with file not found error for ./app/start.sh
- Error indicates the start.sh file is not present at the expected location within the container filesystem

## Steps to Recreate
1. Run start.sh script 
2. Observe containers starting (supabase-studio, supabase-storage created successfully) 
3. Analytics container appears to run correctly 
4. API container fails with file not found error for ./app/start.sh

## Attempts to Solve the Problem
Identified that the error occurs specifically when trying to execute ./app/start.sh inside the API container. The error suggests the start.sh file is not present at the expected location within the container filesystem.

## Hypotheses

1. **Dockerfile COPY/ADD Instructions** (Most Fundamental)
   - hypothesis: Dockerfile.api does not properly copy start.sh to the container
   - null hypothesis: Dockerfile.api correctly copies start.sh to the expected location

2. **File Path in Container**
   - hypothesis: start.sh exists but is in wrong location within container filesystem
   - null hypothesis: start.sh is in the correct ./app/ directory within container

3. **File Permissions**
   - hypothesis: start.sh exists but lacks execute permissions within container
   - null hypothesis: start.sh has proper execute permissions

4. **Docker Build Context**
   - hypothesis: start.sh is not included in Docker build context sent to daemon
   - null hypothesis: start.sh is properly included in build context

5. **Container Working Directory**
   - hypothesis: Container working directory is incorrect, making ./app/start.sh path invalid
   - null hypothesis: Container working directory is set correctly for ./app/start.sh path

6. **Docker Compose Configuration** (Most Dependent)
   - hypothesis: docker-compose.yml has incorrect command or entrypoint configuration
   - null hypothesis: docker-compose.yml correctly references ./app/start.sh

## Investigation Process

Following systematic null hypothesis testing approach:
1. Each hypothesis will be tested with live container evidence
2. Evidence must come from actual container inspection, not code analysis
3. Null hypotheses proven true will eliminate that cause
4. Continue until root cause is identified

## Evidence Collection Standards
- ONLY accept direct evidence from live container inspection
- Use docker exec, docker inspect, docker logs for evidence
- Require actual file system state within containers
- Document timestamps and exact container states

## Analysis of Configuration Files

### Key Findings:
1. **Dockerfile.api Analysis**:
   - Line 12: `ADD app/ /app` - copies entire app directory to /app in container
   - Line 14: `RUN chmod +x /app/start.sh` - sets execute permissions on start.sh
   - Line 18: `CMD ["/app/start.sh"]` - runs start.sh as entrypoint
   - **CRITICAL**: The Dockerfile expects start.sh to be at `/app/start.sh` in container

2. **Docker Compose Configuration**:
   - API service uses `context: ..` (parent directory) for build context
   - Volume mount: `./../app/:/app` - mounts host app/ directory to container /app
   - **POTENTIAL ISSUE**: Volume mount may override the copied files from Dockerfile

3. **File Locations**:
   - Host: `app/start.sh` exists and is executable
   - Container expectation: `/app/start.sh`
   - Volume mount overwrites: Container /app gets replaced by host app/ directory

## Initial Hypothesis Assessment

**MOST LIKELY CAUSE**: The volume mount `./../app/:/app` in docker-compose.launchpad.yml line 14 is overriding the files copied during the Docker build process, including the start.sh file that was made executable in the Dockerfile.

This creates a race condition where:
1. Dockerfile copies app/ and makes start.sh executable
2. Docker Compose volume mount replaces /app with host directory
3. Host start.sh may not have execute permissions or may not exist at expected path

## Next Steps: Live Container Investigation
Need to verify this hypothesis with actual container evidence.

## LIVE CONTAINER EVIDENCE - HYPOTHESIS TESTING

### Hypothesis 1: Dockerfile COPY/ADD Instructions (TESTED)
**Evidence from container inspection:**
```
docker run --rm --entrypoint /bin/sh cedar-heights-backend-api -c "ls -la /app/"
total 24
drwxr-xr-x  1 root root 4096 Sep  8 17:08 .
drwxr-xr-x  1 root root 4096 Sep  8 21:10 ..
drwxr-xr-x 14 root root 4096 Sep  8 16:24 app    <-- APP DIRECTORY EXISTS
drwxr-xr-x  4 root root 4096 Sep  8 17:08 build
drwxr-xr-x  2 root root 4096 Sep  8 17:08 genai_launchpad.egg-info
-rw-r--r--  1 root root  940 Sep  7 18:53 pyproject.toml
```

**Evidence from nested app directory:**
```
docker run --rm --entrypoint /bin/sh cedar-heights-backend-api -c "ls -la /app/app/"
-rwxr-xr-x  1 root root  163 Sep  7 14:03 start.sh    <-- START.SH EXISTS AND IS EXECUTABLE
```

**NULL HYPOTHESIS RESULT**: FALSE - The null hypothesis is disproven
**CONCLUSION**: The Dockerfile DOES copy files correctly, but creates nested structure `/app/app/` instead of `/app/`

### ROOT CAUSE IDENTIFIED

**CONFIRMED ISSUE**: Path mismatch in Dockerfile CMD
- **Container reality**: start.sh is located at `/app/app/start.sh`
- **Dockerfile CMD**: Tries to execute `./app/start.sh` from `/app` working directory
- **Correct path should be**: `./app/start.sh` (relative) or `/app/app/start.sh` (absolute)

**Why this happened**: 
- Dockerfile line 12: `ADD app/ /app` copies the `app/` directory TO `/app`, creating `/app/app/`
- Dockerfile line 18: `CMD ["/app/start.sh"]` expects start.sh directly in `/app`
- The paths don't match due to the nested directory structure

**SOLUTION**: Fix the CMD path in Dockerfile to point to the correct location.