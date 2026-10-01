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
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name="companies")
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
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name="reports")
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
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name="total_counts")
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
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True, blank=True, related_name="expert_words")
    expert = models.ForeignKey(Expert, on_delete=models.CASCADE, related_name='word_lists')
    name = models.CharField(max_length=100, null=True, blank=True)
    words = JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.expert.user.username})"


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