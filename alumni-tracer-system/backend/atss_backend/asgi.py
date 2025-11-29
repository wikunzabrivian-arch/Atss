# asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack # <--- REMOVE THIS IMPORT

import chat.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

# This is a basic, non-authenticating routing structure
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter( # <--- REPLACED AuthMiddlewareStack with just URLRouter
        chat.routing.websocket_urlpatterns
    ),
})