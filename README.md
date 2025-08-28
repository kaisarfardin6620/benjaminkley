## Running the Project with Docker

This project is containerized using Docker and Docker Compose for streamlined development and deployment. Below are the instructions and requirements specific to this setup.

### Project-Specific Docker Requirements
- **Python Version:** 3.13 (as specified in the Dockerfile: `FROM python:3.13-slim`)
- **Dependencies:** All Python dependencies are installed from `requirements.txt` inside a virtual environment (`.venv`).
- **Entrypoint:** The application runs via Gunicorn, serving the Django app defined in `benjaminkley.wsgi:application`.

### Environment Variables
- The Docker Compose file references an optional `.env` file for environment variables. Uncomment the `env_file: ./.env` line in `docker-compose.yml` if you have project-specific environment variables to set.

### Build and Run Instructions
1. **Build and start the application:**
   ```sh
   docker compose up --build
   ```
   This will build the image and start the Django application in a container named `python-app`.

2. **Accessing the application:**
   - The Django app is exposed on port **8000**. Access it at `http://localhost:8000`.

### Special Configuration
- **User Permissions:** The container runs as a non-root user (`appuser`) for improved security.
- **Virtual Environment:** All Python dependencies are installed in `/app/.venv` and the container's `PATH` is set accordingly.
- **Static/Media Files:** If your project uses static or media files, ensure the appropriate Django settings are configured for serving these in production.
- **Additional Services:** If you add a database or cache, update `docker-compose.yml` to include those services and set `depends_on` as needed.

### Ports
- **python-app:** Exposes port **8000** (mapped to host port 8000).

---
*Ensure your `.env` file (if used) is present at the project root and contains all necessary environment variables for your Django settings.*
