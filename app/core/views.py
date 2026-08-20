from django.shortcuts import redirect, render


def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'base.html')
