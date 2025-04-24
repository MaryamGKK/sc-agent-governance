#!/bin/bash
# Create a virtual environment
python3 -m venv uc-env
source uc-env/bin/activate

# Install required Python packages
pip install -r requirements.txt

# Start Unity Catalog via Docker
docker compose -f docker-compose.yml up -d

# Wait for Unity Catalog to be available
echo "⏳ Waiting for Unity Catalog to become available..."
until curl --output /dev/null --silent --head --fail http://localhost:8080/health; do
  printf '.'
  sleep 2
done
echo "✅ Unity Catalog is ready."

# Print activation instructions
echo "To activate this environment in the future, run:"
echo "source uc-env/bin/activate"
