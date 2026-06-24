from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True, default='profile_pics/default.jpg')
    creation_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class Expert(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='expert_profile')
    profession = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.user.username