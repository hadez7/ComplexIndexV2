from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from .forms import CustomUserCreationForm
from django.contrib import messages
from django.contrib.auth import login


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # loguea al usuario automáticamente
            messages.success(request, 'Tu cuenta ha sido creada con éxito. Ahora puedes iniciar sesión.')
            return redirect('index')  # redirige al inicio
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})


def profile_view(request):
    user = request.user
    profile = user.profile  # Accede al perfil vinculado

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        picture = request.FILES.get('profile_picture')

        # Actualiza campos
        if username:
            user.username = username
        if email:
            user.email = email
        user.save()

        if picture:
            profile.picture = picture
            profile.save()

        return redirect('profile')  # Nombre de tu URL para el perfil

    return render(request, 'profile.html')