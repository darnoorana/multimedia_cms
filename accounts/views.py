
# Create your views here.

# accounts/views.py - مشاهد بسيطة للحسابات

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('core:home')

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('core:home')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {
        'user': request.user
    })

