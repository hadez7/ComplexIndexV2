from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
import json
from ..models import Company, Province


@login_required
def company_view(request):
    companies = Company.objects.all()
    provinces = Province.objects.all()
    return render(
        request,
        "companies.html",
        {
            "companies": companies,
            "provinces": provinces,
        },
    )


@login_required
def see_company_json(request, company_id):
    company = Company.objects.get(id=company_id)
    data = {"ruc": company.ruc, "name": company.name, "province": company.province.name}
    return JsonResponse(data)


@csrf_exempt
def create_company(request):
    if request.method == "POST":
        ruc = request.POST.get("ruc")
        name = request.POST.get("name")
        province_id = request.POST.get("province")
        errors = {}

        if not ruc:
            errors["ruc"] = ["Este campo es obligatorio."]
        if not name:
            errors["name"] = ["Este campo es obligatorio."]
        if not province_id:
            errors["province"] = ["Este campo es obligatorio."]
        else:
            try:
                province = Province.objects.get(id=province_id)
            except Province.DoesNotExist:
                errors["province"] = ["Provincia no válida."]

        if errors:
            return JsonResponse({"errors": errors}, status=400)

        company = Company.objects.create(ruc=ruc, name=name, province=province)

        return JsonResponse(
            {
                "id": company.id,
                "ruc": company.ruc,
                "name": company.name,
                "province": company.province.name,
            }
        )

    return JsonResponse({"error": "Método no permitido"}, status=405)


@login_required
def delete_company(request, company_id):
    Company.objects.filter(id=company_id).delete()
    return HttpResponse(status=204)


@csrf_exempt
def update_company(request, company_id):
    company = Company.objects.get(id=company_id)
    data = json.loads(request.body)

    ruc = data.get("ruc")
    name = data.get("name")
    province_id = data.get("province")

    if not (ruc and name and province_id):
        return JsonResponse({"error": "Faltan datos"}, status=400)

    try:
        province = Province.objects.get(id=province_id)
    except Province.DoesNotExist:
        return JsonResponse({"error": "Provincia inválida"}, status=400)

    company.ruc = ruc
    company.name = name
    company.province = province
    company.save()

    return JsonResponse({"success": True})
