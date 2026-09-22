from django.contrib.auth.models import User
from django.db import models
from django.db.models import JSONField
from User.models import Expert

# Create your models here.


class Province(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}"


class Company(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE, null=True, blank=True)
    ruc = models.CharField(max_length=11, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} - {self.ruc}"


class Report(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    file = models.FileField(upload_to="reportes/")
    upload_date = models.DateTimeField(auto_now_add=True)
    extracted_text = models.TextField(null=True,blank=True)
    total_syllables = models.PositiveIntegerField(null=True,blank=True)
    
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
    word = models.CharField(max_length=100, unique=True)
    quantity = models.PositiveIntegerField()

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
    review = models.ForeignKey(ConcealmentReview,on_delete=models.CASCADE)
    paragraph_text = models.TextField()
    occurrences = models.IntegerField()
    discarded = models.BooleanField(default=False)