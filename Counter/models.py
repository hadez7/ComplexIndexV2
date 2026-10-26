from django.contrib.auth.models import User
from django.db import models
from django.db.models import JSONField
from User.models import Expert


class Workspace(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nombre")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    project_type = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo de temática")
    color = models.CharField(max_length=30, default="blue", verbose_name="Color identificador")
    icon = models.CharField(max_length=50, default="folder", verbose_name="Icono")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_workspaces", verbose_name="Creado por")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última modificación")
    is_archived = models.BooleanField(default=False, verbose_name="Archivado")

    class Meta:
        verbose_name = "Espacio de trabajo"
        verbose_name_plural = "Espacios de trabajo"
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class WorkspaceMembership(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('editor', 'Editor / Auditor'),
        ('viewer', 'Lector'),
    ]
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workspace_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='admin')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('workspace', 'user')
        verbose_name = "Membresía de espacio"
        verbose_name_plural = "Membresías de espacios"

    def __str__(self):
        return f"{self.user.username} - {self.workspace.name} ({self.role})"


class Province(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}"


class Company(models.Model):
    # PROTECT: nunca se puede borrar un espacio que tenga empresas (y por ende sus reportes y PDFs).
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="companies")
    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True)
    ruc = models.CharField(max_length=11)
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ('workspace', 'ruc')

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.ruc}"


class Report(models.Model):
    # PROTECT: borrar el espacio no puede arrastrar los reportes ni sus PDFs en disco
    # (la señal pre_delete de Report borra el archivo físico).
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="reports")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    file = models.FileField(upload_to="reportes/")
    upload_date = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(null=True, blank=True)
    total_syllables = models.PositiveIntegerField(null=True, blank=True)
    
    # Métricas de complejidad
    total_words = models.PositiveIntegerField(null=True, blank=True)
    unique_words = models.PositiveIntegerField(null=True, blank=True)
    total_sentences = models.PositiveIntegerField(null=True, blank=True)
    avg_word_length = models.FloatField(null=True, blank=True)
    avg_sentence_length = models.FloatField(null=True, blank=True)
    technical_words_count = models.PositiveIntegerField(null=True, blank=True)
    inflesz_score = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Reporte {self.year} - {self.name}"


class TotalCount(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="total_counts")
    word = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = ('workspace', 'word')

    def __str__(self):
        return f"{self.word} - {self.quantity}"


class TotalCountReport(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    word = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = ('report', 'word')
    
    def __str__(self):
        return f"{self.word} - {self.quantity}"
    
    
class ExpertWord(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="expert_words")
    expert = models.ForeignKey(Expert, on_delete=models.CASCADE, related_name='word_lists')
    name = models.CharField(max_length=100, null=True, blank=True)
    words = JSONField(default=list, blank=True, null=True)

    class Meta:
        # Una misma lista (incluso con el mismo nombre) puede existir en cada espacio,
        # pero nunca dos veces dentro del mismo espacio para el mismo experto.
        unique_together = ('workspace', 'expert', 'name')
        verbose_name = "Lista de palabras de experto"
        verbose_name_plural = "Listas de palabras de expertos"

    def __str__(self):
        return f"{self.name} ({self.expert.user.username})"

    @property
    def monogram(self):
        """Genera el monograma de 2 letras mayúsculas para la insignia circular estilo Figma."""
        if not self.name:
            return "VC"
        stop_words = {"de", "del", "la", "las", "el", "los", "y", "en", "a", "por", "para", "con"}
        clean_parts = [w for w in self.name.split() if w.lower() not in stop_words and w]
        if len(clean_parts) >= 2:
            return (clean_parts[0][0] + clean_parts[1][0]).upper()
        elif len(clean_parts) == 1 and len(clean_parts[0]) >= 2:
            return clean_parts[0][:2].upper()
        elif len(clean_parts) == 1:
            return (clean_parts[0][0] + "L").upper()
        return "VC"

    @property
    def color_theme(self):
        """Asigna una paleta semántica armónica de tokens ELI para la insignia circular."""
        themes = [
            {"badge": "border-[rgba(99,161,255,0.3)] bg-[var(--blue-soft)] text-[var(--blue)]", "pill": "text-[var(--blue)]"},
            {"badge": "border-[rgba(75,212,232,0.3)] bg-[var(--teal-soft)] text-[var(--teal)]", "pill": "text-[var(--teal)]"},
            {"badge": "border-[rgba(129,140,248,0.3)] bg-[var(--indigo-soft)] text-[var(--indigo)]", "pill": "text-[var(--indigo)]"},
            {"badge": "border-[rgba(245,158,11,0.3)] bg-[rgba(245,158,11,0.12)] text-[var(--amber)]", "pill": "text-[var(--amber)]"},
            {"badge": "border-[rgba(52,211,153,0.3)] bg-[rgba(52,211,153,0.12)] text-[var(--green)]", "pill": "text-[var(--green)]"},
        ]
        return themes[(self.id or 0) % len(themes)]

    @property
    def parsed_words(self):
        """
        Devuelve una lista de dicts [{'term': '...', 'weight': 'alta'|'media'|'normal', 'raw': '...'}]
        compatible con strings simples, dicts o formato 'termino:peso'.
        """
        result = []
        if not self.words:
            return result
        for item in self.words:
            if isinstance(item, dict):
                term = str(item.get("term", "")).strip()
                weight = str(item.get("weight", "normal")).lower()
            elif isinstance(item, str):
                if ":" in item:
                    parts = item.split(":", 1)
                    term = parts[0].strip()
                    weight = parts[1].strip().lower()
                else:
                    term = item.strip()
                    weight = "normal"
            else:
                term = str(item).strip()
                weight = "normal"
            if term:
                if weight not in ("alta", "media", "normal", "baja"):
                    weight = "normal"
                result.append({
                    "term": term,
                    "weight": weight,
                    "raw": f"{term}:{weight}" if weight != "normal" else term,
                })
        return result

    @property
    def raw_terms_string(self):
        """Devuelve los términos separados por coma para copiar o editar en texto plano."""
        return ", ".join(item["term"] for item in self.parsed_words)

    @property
    def clean_words(self):
        """Lista plana con los nombres canónicos de los términos."""
        return [item["term"] for item in self.parsed_words]


class ConcealmentReview(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='concealment_reviews')
    word = models.CharField(max_length=100)

    total_found = models.IntegerField()
    total_valid = models.IntegerField()
    total_discarded = models.IntegerField()

    reviewed_at = models.DateTimeField(auto_now=True)      


class ConcealmentParagraphReview(models.Model):
    review = models.ForeignKey(ConcealmentReview, on_delete=models.CASCADE)
    paragraph_text = models.TextField()
    occurrences = models.IntegerField()
    discarded = models.BooleanField(default=False)