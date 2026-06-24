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


class ComparativeAnalysisForm(forms.Form):

    year = forms.ChoiceField(
        label="Año",
        required=False,
        choices=[],
        widget=forms.Select(
            attrs={
                "class": "w-full border border-gray-300 rounded px-3 py-2"
            }
        )
    )

    report = forms.ModelChoiceField(
        queryset=Report.objects.none(),
        label="Reporte",
        widget=forms.Select(
            attrs={
                "class": "w-full border border-gray-300 rounded px-3 py-2"
            }
        )
    )

    expert_list = forms.ModelChoiceField(
        queryset=ExpertWord.objects.all(),
        label="Lista de experto",
        widget=forms.Select(
            attrs={
                "class": "w-full border border-gray-300 rounded px-3 py-2"
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
            ).order_by("name")

