from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from .workspace_utils import get_active_workspace


class WorkspaceAccessGuardMiddleware:
    """
    Denegar por defecto: un usuario sin espacio de trabajo activo no llega a
    ninguna vista con datos.

    Un usuario recién registrado (o al que le han quitado el acceso) no ve nada
    del trabajo hecho: se le redirige a /workspaces/, donde un administrador
    puede añadirlo a un espacio. Los staff/superusuarios ven todos los espacios
    porque son quienes aprueban los accesos.

    Este middleware es la primera barrera; además las vistas filtran siempre por
    el espacio activo, de modo que aunque alguna vista se escape de aquí,
    "sin espacio activo" se traduce en "sin resultados" y nunca en "todo".
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Rutas que se pueden visitar sin espacio activo (login, registro, la
        # propia pantalla de espacios, idioma, estáticos...).
        self.public_paths = tuple(
            path
            for path in getattr(settings, "WORKSPACE_PUBLIC_PATHS", ())
            if path and path != "/"
        )

    def __call__(self, request):
        if not self._es_publica(request.path_info):
            user = getattr(request, "user", None)
            if (
                user is not None
                and user.is_authenticated
                and not user.is_staff
                and not user.is_superuser
                and get_active_workspace(request) is None
            ):
                return self._sin_acceso(request)

        return self.get_response(request)

    # ------------------------------------------------------------------ helpers
    def _es_publica(self, path):
        return any(path.startswith(prefix) for prefix in self.public_paths)

    @staticmethod
    def _es_ajax(request):
        accept = request.headers.get("Accept", "")
        content_type = request.headers.get("Content-Type", "")
        return (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in accept
            or content_type.startswith("application/json")
        )

    @staticmethod
    def _sin_acceso(request):
        # Una llamada AJAX/JSON no debe recibir un HTML con redirect: se responde
        # con 403 para que el JavaScript muestre el error correspondiente.
        if WorkspaceAccessGuardMiddleware._es_ajax(request):
            return JsonResponse(
                {
                    "error": _("No tienes un espacio de trabajo activo."),
                    "detail": "no_active_workspace",
                },
                status=403,
            )

        messages.warning(
            request,
            _(
                "Aún no tienes acceso a ningún espacio de trabajo. "
                "Pídeselo a un administrador para que te añada a uno."
            ),
        )
        return redirect("workspaces_list")
