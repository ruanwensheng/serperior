# How to Dockerize Your FastAPI App

Docker allows you to package your application and all its dependencies (Python, libraries, OS settings) into a single "Container" that runs independently.

Here is the step-by-step guide to Dockerizing `Serperior`.

## Step 1: Create the `Dockerfile`

Create a file named `Dockerfile` (no extension) inside your `backend` folder `e:\Projects\Serperior\backend\Dockerfile`.

Copy this content into it:

```dockerfile
# 1. Base Image: Start with a lightweight Python 3.9 Linux OS
FROM python:3.9-slim

# 2. Work Directory: All following commands happen inside /app
WORKDIR /app

# 3. System Dependencies: Install build tools needed for some ML libraries
# (Optional, but good safety for libraries like wordcloud/chromadb)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy Requirements: Copy only the file first to leverage Docker Cache
COPY requirements.txt .

# 5. Install Dependencies: This runs pip inside the container
# --no-cache-dir reduces image size
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy Code: IMPORTANT! Copy the 'serperior' folder properly
# Since your main.py is in 'backend/', and imports 'serperior', we copy everything in backend
COPY . .

# 7. Command: What runs when the container starts?
# We point to main.py or run uvicorn directly
# Here we verify paths: uvicorn serperior.api.api:app
CMD ["uvicorn", "serperior.api.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Step 2: Build the Image

Open your terminal in `e:\Projects\Serperior\backend` and run:

```bash
docker build -t serperior-backend .
```

*   `-t serperior-backend`: Tags (names) the image.
*   `.`: Tells Docker to look for the `Dockerfile` in the current directory.

*Note: This will take a few minutes as it downloads PyTorch and other heavy libraries.*

## Step 3: Run the Container

Once built, run it:

```bash
docker run -p 8000:8000 serperior-backend
```

*   `-p 8000:8000`: Maps port 8000 on your Windows machine to port 8000 inside the container.
*   The API will now be available at `http://localhost:8000`.

## Step 4: Docker Compose (The Pro Way)

Instead of running long commands, we use `docker-compose`.

Create a file `e:\Projects\Serperior\docker-compose.yml` (in the root, outside backend):

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app  # Live reload! Changes in Windows update the container
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
```

Run it with:
```bash
docker-compose up --build
```

## Explanation of Key Concepts

*   **FROM**: Like installing an OS (e.g., "Install Windows"). We use `python:3.9-slim` (a Linux version with Python pre-installed).
*   **COPY**: Like dragging files from your desktop into the virtual machine.
*   **RUN**: Running terminal commands inside the setup process (like `pip install`).
*   **CMD**: The startup script.
