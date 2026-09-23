from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=False,
        label="Nombre(s)",
        widget=forms.TextInput(attrs={'placeholder': 'Ej. Carlos'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        label="Apellidos",
        widget=forms.TextInput(attrs={'placeholder': 'Ej. Mendoza'})
    )
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'placeholder': 'nombre@ejemplo.com'})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        labels = {
            'username': 'Nombre de usuario',
            'first_name': 'Nombre(s)',
            'last_name': 'Apellidos',
            'email': 'Correo electrónico',
            'password1': 'Contraseña',
            'password2': 'Confirmar contraseña',
        }
        help_texts = {
            'username': '',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            self.fields['username'].widget.attrs.update({'placeholder': 'Ej. auditor_carlos', 'autofocus': 'autofocus'})
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({'placeholder': '••••••••'})
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({'placeholder': '••••••••'})
