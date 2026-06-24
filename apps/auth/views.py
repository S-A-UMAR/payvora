from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.auth.models import Profile
from apps.dashboard.models import Notification

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_overview')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        referral_code = request.POST.get('referral_code', '').strip()

        # Validations
        if password != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/register.html', {'values': request.POST})
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'auth/register.html', {'values': request.POST})
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'auth/register.html', {'values': request.POST})
        if Profile.objects.filter(phone=phone).exists():
            messages.error(request, 'Phone number already registered.')
            return render(request, 'auth/register.html', {'values': request.POST})
        if len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'auth/register.html', {'values': request.POST})

        # Resolve referral
        referrer = None
        if referral_code:
            try:
                ref_profile = Profile.objects.get(referral_code=referral_code)
                referrer = ref_profile.user
            except Profile.DoesNotExist:
                messages.warning(request, 'Invalid referral code – ignored.')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.profile.phone = phone
        if referrer:
            user.profile.referred_by = referrer
        user.profile.save()

        # Create wallet specifically (signals will handle creation, but let's double-check safety)
        if not hasattr(user, 'wallet'):
            from apps.dashboard.models import Wallet
            Wallet.objects.create(user=user)

        # Welcome notification
        Notification.objects.create(
            user=user,
            title='Welcome to Payvora! 🎉',
            message='Your account has been created. Fund your wallet to get started!',
            icon='🎉',
        )

        login(request, user)
        messages.success(request, f'Welcome, {username}! Your account is ready.')
        return redirect('dashboard_overview')
    return render(request, 'auth/register.html', {'values': {}})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_overview')
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            try:
                user_obj = User.objects.get(email=identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'dashboard_overview')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid credentials. Please try again.')
    return render(request, 'auth/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('landing')

@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.save()
        user.profile.phone = request.POST.get('phone', '').strip()
        user.profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    return render(request, 'dashboard/profile.html')
