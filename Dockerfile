# =================================================================
# STAGE 1: Builder - Builds a compatible .whl file using a full build environment
# =================================================================
# Use mambaforge for a faster, more stable build process
FROM condaforge/mambaforge:latest AS builder

# Install build-essential for C extensions
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create the full build environment using Mamba for speed
COPY hummingbot-backend-api/environment.yml .
RUN mamba env create -f environment.yml && \
    mamba clean --all --yes

# Copy Hummingbot source code
COPY hummingbot ./hummingbot-source

# Build the wheel INSIDE the Python 3.12 API environment
WORKDIR /app/hummingbot-source
RUN mamba run -n hummingbot-api python setup.py bdist_wheel


# =================================================================
# STAGE 2: Release - Creates the final, lean API image
# =================================================================
# Start from a fresh mambaforge base to ensure a clean final image
FROM condaforge/mambaforge:latest AS release

# Install runtime OS libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends libusb-1.0-0 && \
    rm -rf /var/lib/apt/lists/*

# 1. Create a NEW, lean runtime environment from our runtime-specific YAML
WORKDIR /app
COPY hummingbot-backend-api/runtime-environment.yml .
RUN mamba env create -f runtime-environment.yml && \
    mamba clean --all --yes

WORKDIR /hummingbot-api

# 2. Install the custom-built wheel from the builder stage
COPY --from=builder /app/hummingbot-source/dist/hummingbot-*.whl .
RUN /opt/conda/envs/hummingbot-api/bin/pip install --no-deps --no-cache-dir hummingbot-*.whl && \
    rm hummingbot-*.whl

# 3. Copy API application source code
COPY hummingbot-backend-api/. .

# 4. Aggressively clean the final environment to reduce size
RUN find /opt/conda/envs/hummingbot-api -type d -name '__pycache__' -exec rm -r '{}' + && \
    find /opt/conda/envs/hummingbot-api -type f -name '*.pyc' -delete && \
    find /opt/conda/envs/hummingbot-api -type f -name '*.a' -delete

# Set the PATH to simplify commands
ENV PATH /opt/conda/envs/hummingbot-api/bin:$PATH

EXPOSE 8000

# Use simplified entrypoint
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]