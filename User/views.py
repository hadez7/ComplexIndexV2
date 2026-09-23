from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from .forms import CustomUserCreationForm
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required


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


@login_required
def profile_view(request):
    user = request.user
    profile = user.profile  # Accede al perfil vinculado

    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        picture = request.FILES.get('profile_picture')

        # Actualiza campos del usuario
        if username:
            user.username = username
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if email:
            user.email = email
        user.save()

        if picture:
            profile.picture = picture
            profile.save()

        messages.success(request, 'Tu perfil ha sido actualizado con éxito.')
        return redirect('profile')

    return render(request, 'profile.html')
