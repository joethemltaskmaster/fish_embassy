from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    return render(request, "inventory/index.html", {
        "active_section": "inventory",
    })