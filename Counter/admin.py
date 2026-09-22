from django.contrib import admin
from .models import Company, Report, TotalCount, Province, TotalCountReport, ExpertWord, ConcealmentReview, ConcealmentParagraphReview

admin.site.register(Company)
admin.site.register(Report)
admin.site.register(TotalCount)
admin.site.register(Province)
admin.site.register(TotalCountReport)
admin.site.register(ExpertWord)
admin.site.register(ConcealmentReview)
admin.site.register(ConcealmentParagraphReview)

