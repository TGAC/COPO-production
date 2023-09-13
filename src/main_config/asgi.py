"""
ASGI config for web project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
#from channels.sessions import SessionMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from channels.routing import ProtocolTypeRouter, URLRouter
import src.apps.copo_core.routing
from django.urls import path
from src.apps.copo_core import consumers

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.main_config.settings.all')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(

            URLRouter(
                src.apps.copo_core.routing.websocket_urlpatterns
            )
        ),
    )
})
