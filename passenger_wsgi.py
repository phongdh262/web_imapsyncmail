import sys
import os

# 1. Add the current directory to sys.path so Python can find 'backend'
#    In cPanel, the root of the app is often where this file lives.
sys.path.insert(0, os.path.dirname(__file__))

# 2. Import the ASGI app
#    Adjust 'backend.main' if your folder structure or file name is different.
from backend.main import app as asgi_app

# 3. Wrap it with a2wsgi to make it WSGI-compatible
from a2wsgi import ASGIMiddleware
application = ASGIMiddleware(asgi_app)
