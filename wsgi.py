# WSGI configuration for PythonAnywhere
# Note: WebSockets (Flask-SocketIO) are NOT supported on PythonAnywhere free tier
# For full multiplayer functionality, consider: Render.com, Railway, or Heroku

import sys
import os

# Add your project directory to the path
project_home = '/home/YOUR_USERNAME/poker_game_follow_queen'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variable for production
os.environ['FLASK_ENV'] = 'production'

from app import app as application

# For PythonAnywhere, the socketio wrapper won't work
# The app will run but without WebSocket support (HTTP fallback only)
