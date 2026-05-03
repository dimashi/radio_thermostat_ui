# Docker Build Process

This directory includes an automated build system for containerizing the Radio Thermostat UI application.

## Files

- **build_docker.py** - Main analysis script that:
  - Traces imports starting from `server/controller.py`
  - Finds all referenced Python modules
  - Locates all HTML and static files
  - Generates a minimal `requirements.txt` with only used packages
  - Generates an optimized `Dockerfile`

- **build.sh** - Shell script that orchestrates the entire build process

- **Dockerfile** - Generated Docker configuration (created by build_docker.py)

- **requirements-minimal.txt** - Generated minimal requirements (created by build_docker.py)

- **.dockerignore** - Specifies files to exclude from Docker build context

## Quick Start

### Option 1: Using the build script (Recommended)

```bash
# Make script executable
chmod +x build.sh

# Build with default image name and tag
./build.sh

# Or specify custom image name and tag
./build.sh my-image v1.0
```

### Option 2: Manual process

```bash
# Step 1: Analyze dependencies
python build_docker.py

# Step 2: Review generated files
cat requirements-minimal.txt
cat Dockerfile

# Step 3: Build Docker image
docker build -t radio-thermostat-ui:latest .
```

## How It Works

### Dependency Analysis (build_docker.py)

1. **Python Import Tracing**
   - Starts from `server/controller.py`
   - Uses AST parsing to extract imports
   - Recursively follows local module imports (schedule_dto.py, state_dto.py, server.py)
   - Collects all external package names

2. **HTML/Static File Discovery**
   - Identifies HTML files served by the application
   - Scans HTML files for script/link references
   - Recursively follows cross-references

3. **Dependency Filtering**
   - Reads `requirements.txt`
   - Maps package names to extracted imports
   - Creates `requirements-minimal.txt` with only used packages
   - Typically reduces ~5 packages to ~3 packages

4. **Dockerfile Generation**
   - Creates lean Dockerfile using `python:3.12-slim` base
   - Installs only necessary dependencies
   - Copies only required application files
   - Configures proper entrypoint


## Running the Container

### Basic usage
```bash
docker run -p 8080:8080 radio-thermostat-ui:latest
```

The application will be available at `http://localhost:8080`

### With thermostat configuration
```bash
docker run -p 8080:8080 radio-thermostat-ui:latest
```

(Note: Thermostat IP is currently hardcoded in code; modify as needed)

### Interactive/Debug mode
```bash
docker run -it -p 8080:8080 radio-thermostat-ui:latest /bin/bash
```

## Advantages of This Approach

✅ **Minimal dependencies** - Only includes packages actually used
✅ **Smaller image size** - ~200MB vs ~300MB+ for full stack
✅ **Faster builds** - Fewer dependencies to download and install
✅ **Automatic** - Re-run script after adding new dependencies
✅ **Maintainable** - Clear separation of concerns
✅ **Version aware** - Documents which packages are required

## Troubleshooting

### "scheduler.html not found"
- Verify the HTML file exists at `client/components/table_scheduler/scheduler.html`
- Check the path references in `server/controller.py`

### Import errors in container
- Re-run `build_docker.py` to update dependencies
- Check if new imports are in the analysis

### Build fails due to missing dependencies
- Run `python build_docker.py` again to regenerate Dockerfile
- Verify Python files are being analyzed correctly

## Extending the Build

To add new Python modules or HTML files:

1. Add imports/references to controller.py
2. Re-run `python build_docker.py`
3. Verify new files appear in the analysis output
4. Rebuild the Docker image

The script will automatically detect and include new dependencies.

## Image Size Reference

Example output sizes:
- Base image (python:3.12-slim): ~125MB
- With minimal requirements: ~75MB
- Final application image: ~200MB

(vs ~300MB+ with full requirements)
