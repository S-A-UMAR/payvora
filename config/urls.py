from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Public Pages (Landing)
    path('', include('apps.public.urls')),
    
    # Authentication & Profile (Register, Login, Logout, Profile)
    path('', include('apps.auth.urls')),
    
    # Consolidated Dashboard, APIs, and Webhooks
    path('dashboard/', include('apps.dashboard.urls')),
]
