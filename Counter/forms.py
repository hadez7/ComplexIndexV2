import zipfile
from django import forms
from .models import Report, Company, ExpertWord


class IndividualReportUploadForm(forms.ModelForm):
    overwrite = forms.BooleanField(
        required=False,
        label="Sobrescribir si ya existe",
        help_text="Reemplaza el reporte y recalcula las palabras si ya existe para la misma empresa y año.",
        widget=forms.CheckboxInput(
            attrs={"class": "rounded text-blue-600 focus:ring-blue-500 h-4 w-4 border-gray-300"}
        )
    )

    class Meta:
        model = Report
        fields = ["company", "year", "name", "file"]
        widgets = {
            "company": forms.Select(
                attrs={
                    "class": "w-full border border-gray-300 rounded-xl px-3.5 py-2.5 text-sm text-gray-800 bg-white shadow-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                }
            ),
            "year": forms.NumberInput(
                attrs={
                    "min": 1990,
                    "max": 2099,
                    "placeholder": "Ej: 2024",
                    "class": "w-full border border-gray-300 rounded-xl px-3.5 py-2.5 text-sm text-gray-800 bg-white shadow-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Nombre descriptivo del reporte (opcional)",
                    "class": "w-full border border-gray-300 rounded-xl px-3.5 py-2.5 text-sm text-gray-800 bg-white shadow-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                }
            ),
            "file": forms.ClearableFileInput(
                attrs={
                    "accept": ".pdf",
                    "class": "w-full border border-gray-300 rounded-xl px-3.5 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].required = False
        self.fields["year"].required = False
        self.fields["name"].required = False
        self.fields["file"].required = True

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if not file:
            raise forms.ValidationError("Debes seleccionar un archivo PDF.")

        # 1. Validar extensión
        if not file.name.lower().endswith(".pdf"):
            raise forms.ValidationError("El archivo debe tener formato PDF (.pdf).")

        # 2. Validar tamaño máximo (máx. 100 MB)
        max_size = 100 * 1024 * 1024
        if file.size > max_size:
            size_mb = file.size / (1024 * 1024)
            raise forms.ValidationError(f"El archivo excede el tamaño máximo permitido de 100 MB (tamaño actual: {size_mb:.1f} MB).")

        # 3. Validar cabecera binaria mágica de PDF (%PDF-)
        try:
            header = file.read(5)
            file.seek(0)
            if not header.startswith(b"%PDF-"):
                raise forms.ValidationError("El archivo no es un documento PDF válido o está dañado.")
        except Exception:
            raise forms.ValidationError("No se pudo verificar la integridad del archivo.")

        return file

    def clean(self):
        cleaned_data = super().clean()
        company = cleaned_data.get("company")
        year = cleaned_data.get("year")
        overwrite = cleaned_data.get("overwrite")

        if company and year:
            existing = Report.objects.filter(company=company, year=year).first()
            if existing and not overwrite:
                empresa_nombre = company.name.strip()
                raise forms.ValidationError(
                    f"Ya existe un reporte registrado para '{empresa_nombre}' en el año {year} "
                    f"(ID #{existing.id} - '{existing.name}'). "
                    f"Marca la casilla 'Sobrescribir si ya existe' si deseas reemplazarlo."
                )

        return cleaned_data


class ZipUploadForm(forms.Form):
    zip_file = forms.FileField(
        label="Archivo ZIP",
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".zip",
                "class": "w-full border border-gray-300 rounded-xl px-3.5 py-2 text-sm text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition"
            }
        ),
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=False,
        label="Empresa (opcional si los nombres contienen la empresa)",
        empty_label="-- Detección automática por texto / reporte --",
        widget=forms.Select(
            attrs={
                "class": "w-full border border-gray-300 rounded-xl px-3.5 py-2.5 text-sm text-gray-800 bg-white shadow-xs focus:ring-2 focus:ring-green-500 focus:border-green-500 transition"
            }
        ),
    )
    overwrite = forms.BooleanField(
        required=False,
        label="Sobrescribir reportes existentes",
        help_text="Reemplaza reportes con el mismo nombre si ya están registrados en la empresa.",
        widget=forms.CheckboxInput(
            attrs={"class": "rounded text-green-600 focus:ring-green-500 h-4 w-4 border-gray-300"}
        )
    )

    def clean_zip_file(self):
        zip_file = self.cleaned_data.get("zip_file")
        if not zip_file:
            raise forms.ValidationError("Debes seleccionar un archivo ZIP.")

        if not zip_file.name.lower().endswith(".zip"):
            raise forms.ValidationError("El archivo debe tener extensión .zip.")

        # Límite máx. 300 MB
        max_size = 300 * 1024 * 1024
        if zip_file.size > max_size:
            size_mb = zip_file.size / (1024 * 1024)
            raise forms.ValidationError(f"El archivo ZIP excede los 300 MB permitidos (tamaño actual: {size_mb:.1f} MB).")

        # Validar si es un zip íntegro
        if not zipfile.is_zipfile(zip_file):
            raise forms.ValidationError("El archivo subido no es un comprimido ZIP válido o está corrupto.")

        return zip_file


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

        if self.data.get("year"):
            self.fields["report"].queryset = Report.objects.filter(
                year=self.data.get("year")
            ).select_related("company").order_by("company__name", "name")
