from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import RegisterForm, LoginForm, UserUpdateForm, ProfileUpdateForm
from portfolio_ai.ratelimit import rate_limit


def register_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Account created.')
            return redirect('/dashboard/')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


@rate_limit('login', limit=10, window=300)  # 10 attempts / 5 min per IP
def login_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')

            # Only follow `next` if it's a safe, same-site redirect target —
            # otherwise this is an open-redirect vector (e.g. ?next=https://evil.com).
            next_url = request.GET.get('next', '/dashboard/')
            if not url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                next_url = '/dashboard/'
            return redirect(next_url)
        messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm(request)
    return render(request, 'users/login.html', {'form': form})


@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('users:login')
    return redirect('/dashboard/')


@login_required
def profile_view(request):
    if request.method == 'POST':
        user_form    = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated!')
            return redirect('users:profile')
        messages.error(request, 'Please fix the errors below.')
    else:
        user_form    = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    return render(request, 'users/profile.html', {'user_form': user_form, 'profile_form': profile_form})