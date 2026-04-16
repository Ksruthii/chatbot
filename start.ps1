#!/usr/bin/env python
import os
import sys
from flask import Flask
from app import init_db

# Initialize database
init_db()

# Get port from environment or default to 5000
port = int(os.environ.get('PORT', 5000))

# Run the app
if __name__ == '__main__':
    from app import app
    app.run(host='0.0.0.0', port=port, debug=True)
