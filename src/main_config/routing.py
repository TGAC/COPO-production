from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import src.apps.copo_core.routing

application = ProtocolTypeRouter({
    'websocket': SessionMiddlewareStack(
        AuthMiddlewareStack(

            URLRouter(
                src.apps.copo_core.routing.websocket_urlpatterns
            )
        ),
    )
})
