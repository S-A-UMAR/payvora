from django.shortcuts import render, redirect

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard_overview')
    return render(request, 'public/landing.html')
