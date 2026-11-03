from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render


@login_required
@permission_required("sales.add_sale", raise_exception=True)
def index(request):
    return render(request, "sales/index.html", {
        "active_section": "sales",
    })