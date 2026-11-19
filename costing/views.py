from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from .models import OperatingExpense
from .forms import OperatingExpenseForm


@login_required
@permission_required("costing.view_operatingexpense", raise_exception=True)
def expenses_list(request):
    expenses = OperatingExpense.objects.all().order_by("-date")
    page = Paginator(expenses, 25).get_page(request.GET.get("page", 1))

    return render(request, "costing/expenses/list.html", {
        "active_section": "costing",
        "rows": page.object_list,
        "page": page
    })


@login_required
@permission_required("costing.add_operatingexpense", raise_exception=True)
def expense_create(request):
    if request.method == "POST":
        form = OperatingExpenseForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.recorded_by = request.user
            obj.save()
            messages.success(request, "Expense recorded successfully.")
            return redirect("expenses_list")
    else:
        form = OperatingExpenseForm()

    return render(request, "costing/expenses/create.html", {
        "active_section": "costing",
        "form": form
    })