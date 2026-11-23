import json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .orchestrator import process_chat_message


def superuser_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("Access restricted to System Superusers.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


@superuser_required
def chat_interface(request):
    return render(request, "business_ai/chat.html", {
        "active_section": "business_intelligence"
    })


@superuser_required
@csrf_exempt
def chat_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message")
        history = data.get("history", [])

        if not user_message:
            return JsonResponse({"error": "Message is required."}, status=400)

        result = process_chat_message(user_message, history)

        if "error" in result:
            return JsonResponse(result, status=500)

        return JsonResponse(result)
    return JsonResponse({"error": "POST required."}, status=405)