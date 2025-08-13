# =================================================================
# STAGE 1: Builder - Builds a compatible .whl file
# =================================================================
FROM continuumio/miniconda3:latest AS builder

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Create the final API environment from its YAML file
COPY hummingbot-backend-api/environment.yml .
RUN conda env create -f environment.yml

# Install BUILD dependencies into the created environment
RUN conda run -n hummingbot-api pip install --no-cache-dir cython "numpy<2.0.0" wheel setuptools

# Copy Hummingbot source code (this works because the build context is the parent dir)
COPY hummingbot ./hummingbot-source

# Build the wheel INSIDE the Python 3.12 API environment
WORKDIR /app/hummingbot-source
RUN conda run -n hummingbot-api python setup.py bdist_wheel


# =================================================================
# STAGE 2: Release - Creates the final API image
# =================================================================
FROM continuumio/miniconda3:latest AS release

RUN apt-get update && apt-get install -y --no-install-recommends libusb-1.0-0 && rm -rf /var/lib/apt/lists/*

# Copy the complete, pre-built conda environment from the builder
COPY --from=builder /opt/conda/envs/hummingbot-api /opt/conda/envs/hummingbot-api
WORKDIR /hummingbot-api

# Install the custom-built, compatible wheel
COPY --from=builder /app/hummingbot-source/dist/hummingbot-*.whl .
RUN /opt/conda/envs/hummingbot-api/bin/pip install --no-deps --no-cache-dir hummingbot-*.whl && rm hummingbot-*.whl

# Copy API application source code
COPY hummingbot-backend-api/. .

EXPOSE 8000
ENTRYPOINT ["/opt/conda/envs/hummingbot-api/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]