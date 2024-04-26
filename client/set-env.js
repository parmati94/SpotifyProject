// set-env.js
const fs = require('fs');
const path = require('path');

// Provide a default value if the environment variable is empty
const REACT_APP_API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Path to env-config.js
const configPath = path.join(__dirname, 'public', 'env-config.js');

// Read env-config.js
const configData = fs.readFileSync(configPath, 'utf8');

// Replace the entire line containing REACT_APP_API_BASE_URL with the new value
const result = configData.replace(/(REACT_APP_API_BASE_URL: ).*?(,)?$/gm, `$1"${REACT_APP_API_BASE_URL}"$2`);

// Write the result back to env-config.js
fs.writeFileSync(configPath, result, 'utf8');