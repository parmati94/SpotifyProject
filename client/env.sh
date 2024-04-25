#!/bin/bash

# Provide a default value if the environment variable is empty
REACT_APP_API_BASE_URL=${REACT_APP_API_BASE_URL:-'http://localhost:8000'}

# Replace placeholders in env-config.js with environment variables
sed -i 's|$REACT_APP_API_BASE_URL|'"$REACT_APP_API_BASE_URL"'|' /usr/src/app/build/env-config.js