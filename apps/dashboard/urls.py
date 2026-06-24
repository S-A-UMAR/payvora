from django.urls import path
from . import views

urlpatterns = [
    # UI Views
    path('', views.dashboard_overview, name='dashboard_overview'),
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/fund/', views.fund_wallet_view, name='fund_wallet'),
    path('wallet/process/', views.process_payment, name='process_payment'),
    
    path('buy/data/', views.buy_data, name='buy_data'),
    path('buy/data/purchase/', views.purchase_data, name='purchase_data'),
    path('buy/airtime/', views.buy_airtime, name='buy_airtime'),
    path('buy/electricity/', views.buy_electricity, name='buy_electricity'),
    path('buy/tv/', views.buy_tv, name='buy_tv'),
    path('buy/exam/', views.buy_exam, name='buy_exam'),
    
    path('subscriptions/', views.subscriptions_view, name='subscriptions'),
    path('subscriptions/cancel/<int:sub_id>/', views.cancel_subscription, name='cancel_subscription'),
    path('support/', views.support_view, name='support'),
    path('referrals/', views.referrals_view, name='referrals'),
    path('rewards/', views.rewards_view, name='rewards'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # REST APIs & Webhooks
    path('api/v1/vtu/purchase/', views.VTUPurchaseAPIView.as_view(), name='api_vtu_purchase'),
    path('api/v1/webhooks/monnify/', views.MonnifyWebhookView.as_view(), name='webhook_monnify'),
    path('api/v1/webhooks/paystack/', views.PaystackWebhookView.as_view(), name='webhook_paystack'),
]
