from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=False,
        label=_("Nombre(s)"),
        widget=forms.TextInput(attrs={'placeholder': _('Ej. Carlos')})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        label=_("Apellidos"),
        widget=forms.TextInput(attrs={'placeholder': _('Ej. Mendoza')})
    )
    email = forms.EmailField(
        required=True,
        label=_("Correo electrónico"),
        widget=forms.EmailInput(attrs={'placeholder': _('nombre@ejemplo.com')})
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        labels = {
            'username': _('Nombre de usuario'),
            'first_name': _('Nombre(s)'),
            'last_name': _('Apellidos'),
            'email': _('Correo electrónico'),
            'password1': _('Contraseña'),
            'password2': _('Confirmar contraseña'),
        }
        help_texts = {
            'username': '',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Este correo electrónico ya está registrado."))
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            self.fields['username'].widget.attrs.update({'placeholder': _('Ej. auditor_carlos'), 'autofocus': 'autofocus'})
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({'placeholder': '••••••••'})
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({'placeholder': '••••••••'})
