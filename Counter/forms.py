from django import forms
from .models import Report, Company, ExpertWord


class IndividualReportUploadForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["company", "year", "name", "file"]
        widgets = {
            "company": forms.Select(attrs={"class": "border rounded px-2 py-1"}),
            "year": forms.NumberInput(
                attrs={"min": 2000, "max": 2100, "class": "border rounded px-2 py-1"}
            ),
            "name": forms.TextInput(attrs={"class": "border rounded px-2 py-1"}),
            "file": forms.ClearableFileInput(
                attrs={"class": "border rounded px-2 py-1"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].required = False
        self.fields["year"].required = False
        self.fields["name"].required = False
        self.fields["file"].required = True


class ZipUploadForm(forms.Form):
    zip_file = forms.FileField(
        label="Archivo ZIP",
        widget=forms.ClearableFileInput(attrs={"class": "border rounded px-2 py-1"}),
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "w-full min-w-0 block border rounded px-2 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"}),
    )


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["ruc", "name", "province"]
        widgets = {
            "ruc": forms.TextInput(attrs={"class": "border rounded px-2 py-1"}),
            "name": forms.TextInput(attrs={"class": "border rounded px-2 py-1"}),
            "province": forms.Select(attrs={"class": "border rounded px-2 py-1"}),
        }


class ReportModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        company_name = obj.company.name.strip() if obj.company and obj.company.name else ""
        if company_name:
            if obj.name and obj.name != str(obj.year) and obj.name.lower() != "reporte":
                return f"{company_name} - {obj.name}"
            return company_name
        return obj.name or f"Reporte {obj.id}"


class ComparativeAnalysisForm(forms.Form):
    SELECT_CLASSES = "w-full border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 px-3.5 py-2.5 text-sm text-gray-800 bg-white transition"

    year = forms.ChoiceField(
        label="Año",
        required=False,
        choices=[],
        widget=forms.Select(
            attrs={
                "class": "w-full border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 px-3.5 py-2.5 text-sm text-gray-800 bg-white transition"
            }
        )
    )

    report = ReportModelChoiceField(
        queryset=Report.objects.none(),
        label="Reporte",
        empty_label="Seleccione un reporte",
        widget=forms.Select(
            attrs={
                "class": "w-full border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 px-3.5 py-2.5 text-sm text-gray-800 bg-white transition"
            }
        )
    )

    expert_list = forms.ModelChoiceField(
        queryset=ExpertWord.objects.all(),
        label="Lista de experto",
        empty_label="Seleccione una lista",
        widget=forms.Select(
            attrs={
                "class": "w-full border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 px-3.5 py-2.5 text-sm text-gray-800 bg-white transition"
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        years = (
            Report.objects
            .values_list("year", flat=True)
            .distinct()
            .order_by("-year")
        )

        self.fields["year"].choices = [
            ("", "Seleccione un año")
        ] + [
            (year, year)
            for year in years
            if year
        ]

        # IMPORTANTE
        if self.data.get("year"):
            self.fields["report"].queryset = Report.objects.filter(
                year=self.data.get("year")
            ).select_related("company").order_by("company__name", "name")

