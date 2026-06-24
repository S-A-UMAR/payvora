import uuid
import random
import decimal
import logging
import hmac
import hashlib
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Sum, Count
from django.db import transaction
from django.utils import timezone
import datetime

# DRF imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated

from django.conf import settings
from apps.auth.models import Profile
from apps.dashboard.models import (
    Wallet, Transaction, DataPlan, Subscription, SupportTicket, Badge, UserBadge, Notification
)
from apps.dashboard.tasks import process_vtu_purchase_task

logger = logging.getLogger(__name__)

# ── Helpers ─────────────────────────────────────────────────────────────────

def get_wallet(user):
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet

def detect_network(phone):
    phone = phone.replace(' ', '').replace('-', '')
    if phone.startswith('0'):
        phone = phone[1:]
    mtn = ['0703','0706','0803','0806','0810','0813','0814','0816','0903','0906','0913','0916']
    airtel = ['0701','0708','0802','0808','0812','0901','0902','0904','0907','0912']
    glo = ['0705','0805','0807','0811','0815','0905','0915']
    mobile9 = ['0809','0817','0818','0909','0908']
    full = '0' + phone[:9]
    prefix = full[:4]
    if prefix in mtn: return 'MTN'
    if prefix in airtel: return 'Airtel'
    if prefix in glo: return 'Glo'
    if prefix in mobile9: return '9mobile'
    return None

def add_xp_and_notify(user, xp):
    profile = user.profile
    leveled_up = profile.add_xp(xp)
    profile.save()
    if leveled_up:
        Notification.objects.create(
            user=user,
            title=f'Level Up! You are now Level {profile.level}',
            message='Keep transacting to unlock more badges and rewards!',
            icon='admin'
        )

# ── normal UI dashboard views ──────────────────────────────────────────────

@login_required
def dashboard_overview(request):
    wallet = get_wallet(request.user)
    transactions = Transaction.objects.filter(user=request.user)[:8]
    notifications_unread = Notification.objects.filter(user=request.user, is_read=False).count()
    profile = request.user.profile
    services = [
        ('Buy Data', '📶', reverse('buy_data')),
        ('Buy Airtime', '📞', reverse('buy_airtime')),
        ('Electricity', '⚡', reverse('buy_electricity')),
        ('TV / Cable', '📺', reverse('buy_tv')),
        ('Exam Pins', '📝', reverse('buy_exam')),
        ('Auto-Renew', '🔄', reverse('subscriptions')),
    ]
    return render(request, 'dashboard/overview.html', {
        'wallet': wallet,
        'transactions': transactions,
        'notifications_unread': notifications_unread,
        'profile': profile,
        'services': services,
    })

@login_required
def wallet_view(request):
    wallet = get_wallet(request.user)
    transactions = Transaction.objects.filter(user=request.user)
    return render(request, 'dashboard/wallet.html', {
        'wallet': wallet,
        'transactions': transactions,
    })

@login_required
def fund_wallet_view(request):
    if request.method == 'POST':
        try:
            amount = decimal.Decimal(request.POST.get('amount', '0'))
        except Exception:
            messages.error(request, 'Invalid amount.')
            return redirect('wallet')
        if amount < 100:
            messages.error(request, 'Minimum funding amount is ₦100.')
            return redirect('wallet')
        reference = 'PV-' + str(uuid.uuid4()).replace('-', '')[:16].upper()
        return render(request, 'dashboard/paystack_checkout.html', {
            'amount': amount,
            'reference': reference,
        })
    return redirect('wallet')

@login_required
def process_payment(request):
    if request.method == 'POST':
        reference = request.POST.get('reference', '')
        outcome = request.POST.get('outcome', 'success')
        try:
            amount = decimal.Decimal(request.POST.get('amount', '0'))
        except Exception:
            messages.error(request, 'Invalid payment data.')
            return redirect('wallet')

        wallet = get_wallet(request.user)
        txn = Transaction.objects.create(
            user=request.user,
            wallet=wallet,
            type='fund',
            amount=amount,
            status='pending',
            reference=reference,
            details='Simulated Paystack payment'
        )

        if outcome == 'success':
            wallet.credit_balance(amount)
            # Cashback: 1% on every funding
            cashback = round(amount * decimal.Decimal('0.01'), 2)
            wallet.cashback_balance += cashback
            wallet.save()
            
            txn.status = 'success'
            txn.save()
            
            add_xp_and_notify(request.user, 5)
            
            Notification.objects.create(
                user=request.user,
                title='Wallet Funded',
                message=f'₦{amount:,.2f} has been credited to your Payvora wallet. (Cashback: ₦{cashback:,.2f})',
                icon='fund'
            )
            messages.success(request, f'₦{amount:,.2f} successfully added to your wallet!')
        else:
            txn.status = 'failed'
            txn.save()
            Notification.objects.create(
                user=request.user,
                title='Payment Failed',
                message=f'Your payment of ₦{amount:,.2f} was not successful. Please try again.',
                icon='error'
            )
            messages.error(request, 'Payment failed. Your wallet was not debited.')
        return redirect('wallet')
    return redirect('wallet')

@login_required
def buy_data(request):
    network_filter = request.GET.get('network', 'MTN')
    networks = ['MTN', 'Airtel', 'Glo', '9mobile']
    plans = DataPlan.objects.filter(network=network_filter, active=True)
    wallet = get_wallet(request.user)
    return render(request, 'dashboard/buy_data.html', {
        'plans': plans,
        'networks': networks,
        'selected_network': network_filter,
        'wallet': wallet,
    })

@login_required
def purchase_data(request):
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        phone = request.POST.get('phone', '').strip()
        plan = get_object_or_404(DataPlan, id=plan_id, active=True)
        wallet = get_wallet(request.user)

        try:
            # Immediate debit to hold balance
            wallet.deduct_balance(plan.price)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('buy_data')

        reference = 'PV-' + str(uuid.uuid4()).replace('-', '')[:16].upper()
        details = f'{plan.network} {plan.name} ({plan.volume}) to {phone} CODE:{plan.plan_code}'
        
        txn = Transaction.objects.create(
            user=request.user,
            wallet=wallet,
            type='purchase',
            service='data',
            amount=plan.price,
            status='pending',
            reference=reference,
            details=details
        )
        
        # Dispatch Celery background task
        process_vtu_purchase_task.delay(str(txn.id))
        
        messages.success(request, 'Your data purchase request has been submitted and is processing.')
    return redirect('buy_data')

@login_required
def buy_airtime(request):
    wallet = get_wallet(request.user)
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        network = request.POST.get('network', '').strip()
        try:
            amount = decimal.Decimal(request.POST.get('amount', '0'))
        except Exception:
            messages.error(request, 'Invalid amount.')
            return redirect('buy_airtime')
        if amount < 50:
            messages.error(request, 'Minimum airtime purchase is ₦50.')
            return redirect('buy_airtime')

        try:
            # Immediate debit to hold balance
            wallet.deduct_balance(amount)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('buy_airtime')

        reference = 'PV-' + str(uuid.uuid4()).replace('-', '')[:16].upper()
        details = f'{network} ₦{amount:,.0f} airtime to {phone}'
        
        txn = Transaction.objects.create(
            user=request.user,
            wallet=wallet,
            type='purchase',
            service='airtime',
            amount=amount,
            status='pending',
            reference=reference,
            details=details
        )

        # Dispatch Celery background task
        process_vtu_purchase_task.delay(str(txn.id))
        
        messages.success(request, 'Your airtime purchase request has been submitted and is processing.')
        return redirect('buy_airtime')
    return render(request, 'dashboard/buy_airtime.html', {'wallet': wallet})

@login_required
def buy_electricity(request):
    wallet = get_wallet(request.user)
    discos = ['AEDC (Abuja)', 'EKEDC (Eko)', 'IKEDC (Ikeja)', 'IBEDC (Ibadan)',
              'PHEDC (Port Harcourt)', 'KEDCO (Kano)', 'JEDC (Jos)', 'BEDC (Benin)']
    if request.method == 'POST':
        disco = request.POST.get('disco', '')
        meter = request.POST.get('meter', '').strip()
        meter_type = request.POST.get('meter_type', 'prepaid')
        try:
            amount = decimal.Decimal(request.POST.get('amount', '0'))
        except Exception:
            messages.error(request, 'Invalid amount.')
            return redirect('buy_electricity')
        if amount < 500:
            messages.error(request, 'Minimum electricity payment is ₦500.')
            return redirect('buy_electricity')

        try:
            wallet.deduct_balance(amount)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('buy_electricity')

        reference = 'PV-' + str(uuid.uuid4()).replace('-', '')[:16].upper()
        details = f'{disco} {meter_type.title()} – Meter: {meter} – ₦{amount:,.0f}'
        
        txn = Transaction.objects.create(
            user=request.user,
            wallet=wallet,
            type='purchase',
            service='electricity',
            amount=amount,
            status='pending',
            reference=reference,
            details=details
        )

        process_vtu_purchase_task.delay(str(txn.id))
        messages.success(request, 'Your electricity bill payment is processing.')
        return redirect('buy_electricity')
    return render(request, 'dashboard/buy_electricity.html', {'wallet': wallet, 'discos': discos})

@login_required
def buy_tv(request):
    wallet = get_wallet(request.user)
    providers = {
        'DSTV': [('Padi ₦2,950', 2950), ('Yanga ₦3,600', 3600), ('Confam ₦6,200', 6200),
                 ('Compact ₦10,500', 10500), ('Premium ₦24,500', 24500)],
        'GOtv': [('Supa Plus ₦7,200', 7200), ('Supa ₦5,500', 5500), ('Max ₦4,150', 4150),
                 ('Jolli ₦2,800', 2800), ('Jinja ₦1,900', 1900)],
        'Startimes': [('Nova ₦1,700', 1700), ('Basic ₦2,300', 2300), ('Smart ₦2,800', 2800),
                       ('Classic ₦3,300', 3300), ('Super ₦5,200', 5200)],
    }
    if request.method == 'POST':
        provider = request.POST.get('provider', '')
        smartcard = request.POST.get('smartcard', '').strip()
        package_name = request.POST.get('package', '')
        try:
            amount = decimal.Decimal(request.POST.get('amount', '0'))
        except Exception:
            messages.error(request, 'Invalid amount.')
            return redirect('buy_tv')

        try:
            wallet.deduct_balance(amount)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('buy_tv')

        reference = 'PV-' + str(uuid.uuid4()).replace('-', '')[:16].upper()
        details = f'{provider} {package_name} – Smartcard: {smartcard}'
        
        txn = Transaction.objects.create(
            user=request.user,
            wallet=wallet,
            type='purchase',
            service='tv',
            amount=amount,
            status='pending',
            reference=reference,
            details=details
        )

        process_vtu_purchase_task.delay(str(txn.id))
        messages.success(request, 'Your TV subscription request is processing.')
        return redirect('buy_tv')
    return render(request, 'dashboard/buy_tv.html', {'wallet': wallet, 'providers': providers})

@login_required
def buy_exam(request):
    wallet = get_wallet(request.user)
    exam_types = [
        ('WAEC', 3500), ('NECO', 1000), ('NABTEB', 1500),
        ('JAMB Profile', 700), ('JAMB Mock', 3500),
    ]
    if request.method == 'POST':
        exam = request.POST.get('exam', '')
        quantity = int(request.POST.get('quantity', 1))
        try:
            unit_price = decimal.Decimal(request.POST.get('unit_price', '0'))
        except Exception:
            messages.error(request, 'Invalid price.')
            return redirect('buy_exam')
        amount = unit_price * quantity

        try:
            wallet.deduct_balance(amount)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('buy_exam')

        reference = 'PV-' + str(uuid.uuid4()).replace('-', '')[:16].upper()
        details = f'{exam} – {quantity} pin(s) @ ₦{unit_price:,.0f} each'
        
        txn = Transaction.objects.create(
            user=request.user,
            wallet=wallet,
            type='purchase',
            service='exam',
            amount=amount,
            status='pending',
            reference=reference,
            details=details
        )

        process_vtu_purchase_task.delay(str(txn.id))
        messages.success(request, 'Your exam pin order is processing.')
        return redirect('buy_exam')
    return render(request, 'dashboard/buy_exam.html', {'wallet': wallet, 'exam_types': exam_types})

@login_required
def subscriptions_view(request):
    wallet = get_wallet(request.user)
    plans = DataPlan.objects.filter(active=True)
    subs = Subscription.objects.filter(user=request.user, active=True)
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        phone = request.POST.get('phone', '').strip()
        schedule = request.POST.get('schedule', 'monthly')
        plan = get_object_or_404(DataPlan, id=plan_id)
        Subscription.objects.create(
            user=request.user, plan=plan, service_type='data',
            phone_number=phone, schedule=schedule, amount=plan.price
        )
        messages.success(request, f'Auto-renew for {plan.name} set up successfully!')
        return redirect('subscriptions')
    return render(request, 'dashboard/subscriptions.html', {
        'wallet': wallet, 'plans': plans, 'subs': subs,
    })

@login_required
def cancel_subscription(request, sub_id):
    sub = get_object_or_404(Subscription, id=sub_id, user=request.user)
    sub.active = False
    sub.save()
    messages.success(request, 'Subscription cancelled.')
    return redirect('subscriptions')

@login_required
def support_view(request):
    tickets = SupportTicket.objects.filter(user=request.user)
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        if subject and message:
            SupportTicket.objects.create(user=request.user, subject=subject, message=message)
            messages.success(request, 'Support ticket submitted! We will respond within 24 hours.')
        else:
            messages.error(request, 'Please fill in all fields.')
        return redirect('support')
    return render(request, 'dashboard/support.html', {'tickets': tickets})

@login_required
def referrals_view(request):
    wallet = get_wallet(request.user)
    profile = request.user.profile
    referred_users = User.objects.filter(profile__referred_by=request.user)
    total_commission = Transaction.objects.filter(
        user=request.user, type='commission', status='success'
    ).aggregate(total=Sum('amount'))['total'] or 0
    if request.method == 'POST' and request.POST.get('action') == 'redeem':
        commission_amount = decimal.Decimal(str(total_commission))
        if commission_amount > 0:
            wallet.credit_balance(commission_amount)
            Transaction.objects.filter(user=request.user, type='commission', status='success').update(status='failed')
            messages.success(request, f'₦{commission_amount:,.2f} referral commission redeemed to wallet!')
        else:
            messages.info(request, 'No commission balance to redeem.')
        return redirect('referrals')
    return render(request, 'dashboard/referrals.html', {
        'wallet': wallet, 'profile': profile,
        'referred_users': referred_users, 'total_commission': total_commission,
    })

@login_required
def rewards_view(request):
    wallet = get_wallet(request.user)
    all_badges = Badge.objects.all()
    user_badges = UserBadge.objects.filter(user=request.user).values_list('badge_id', flat=True)
    profile = request.user.profile
    xp_in_level = profile.xp % 100
    xp_needed = 100
    level_percent = int((xp_in_level / xp_needed) * 100)

    if request.method == 'POST' and request.POST.get('action') == 'redeem_cashback':
        cashback = wallet.cashback_balance
        if cashback > 0:
            wallet.credit_balance(cashback)
            
            with transaction.atomic():
                locked_wallet = Wallet.objects.select_for_update().get(id=wallet.id)
                locked_wallet.cashback_balance = 0
                locked_wallet.save()
            
            Transaction.objects.create(
                user=request.user, wallet=wallet, type='cashback_redeem',
                amount=cashback, status='success',
                reference='PV-CB-' + str(request.user.id),
                details='Cashback redeemed to wallet'
            )
            messages.success(request, f'₦{cashback:,.2f} cashback redeemed to your wallet!')
        else:
            messages.info(request, 'No cashback balance to redeem.')
        return redirect('rewards')

    return render(request, 'dashboard/rewards.html', {
        'wallet': wallet,
        'profile': profile,
        'all_badges': all_badges,
        'user_badges': list(user_badges),
        'level_percent': level_percent,
        'xp_in_level': xp_in_level,
    })

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user)
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'dashboard/notifications.html', {'notifications': notifications})

@staff_member_required
def admin_dashboard(request):
    total_users = User.objects.count()
    total_tx = Transaction.objects.count()
    success_tx = Transaction.objects.filter(status='success').count()
    failed_tx = Transaction.objects.filter(status='failed').count()
    
    total_volume = Transaction.objects.filter(status='success').aggregate(total=Sum('amount'))['total'] or 0
    total_cashback = Wallet.objects.aggregate(total=Sum('cashback_balance'))['total'] or 0
    total_wallets = Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0

    if request.method == 'POST':
        ticket_id = request.POST.get('ticket_id')
        action = request.POST.get('action')
        if ticket_id:
            ticket = get_object_or_404(SupportTicket, id=ticket_id)
            if action == 'resolve':
                ticket.status = 'resolved'
                ticket.save()
                messages.success(request, f"Ticket #{ticket.id} resolved successfully.")
            elif action == 'reopen':
                ticket.status = 'open'
                ticket.save()
                messages.success(request, f"Ticket #{ticket.id} reopened.")
            return redirect('admin_dashboard')

    tickets = SupportTicket.objects.all().order_by('-created_at')

    today = timezone.now().date()
    weekly_stats = []
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_tx = Transaction.objects.filter(created_at__date=day)
        count = day_tx.count()
        vol = day_tx.filter(status='success').aggregate(total=Sum('amount'))['total'] or 0
        weekly_stats.append({
            'label': day.strftime('%a'),
            'count': count,
            'volume': float(vol)
        })

    return render(request, 'dashboard/admin_dashboard.html', {
        'total_users': total_users,
        'total_tx': total_tx,
        'success_tx': success_tx,
        'failed_tx': failed_tx,
        'total_volume': total_volume,
        'total_cashback': total_cashback,
        'total_wallets': total_wallets,
        'tickets': tickets,
        'weekly_stats': weekly_stats,
    })

# ── DRF REST API View ───────────────────────────────────────────────────────

class VTUPurchaseSerializer(serializers.Serializer):
    service = serializers.ChoiceField(choices=['data', 'airtime'])
    phone = serializers.CharField(max_length=20)
    network = serializers.ChoiceField(choices=['MTN', 'Airtel', 'Glo', '9mobile'])
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    plan_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    pin = serializers.CharField(max_length=4)

class VTUPurchaseAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = VTUPurchaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        wallet = get_wallet(request.user)

        # Thread-safe PIN verification and balance debiting
        try:
            wallet.deduct_balance(data['amount'], pin_provided=data['pin'])
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        reference = 'API-PV-' + str(uuid.uuid4()).replace('-', '')[:16].upper()
        details = f"{data['network']} {data['service'].upper()} purchase to {data['phone']}"
        if data.get('plan_code'):
            details += f" CODE:{data['plan_code']}"

        txn = Transaction.objects.create(
            user=request.user,
            wallet=wallet,
            type='purchase',
            service=data['service'],
            amount=data['amount'],
            status='pending',
            reference=reference,
            details=details
        )

        # Dispatch Celery background task
        process_vtu_purchase_task.delay(str(txn.id))

        return Response({
            "message": "Transaction processing initiated.",
            "transaction_id": str(txn.id),
            "reference": reference,
            "status": "pending"
        }, status=status.HTTP_202_ACCEPTED)

# ── Payment Webhooks ────────────────────────────────────────────────────────

class MonnifyWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Monnify webhook signature verification
        monnify_signature = request.headers.get('MONNIFY-SIGNATURE', '')
        client_secret = getattr(settings, 'MONNIFY_SECRET_KEY', '')
        
        # Calculate HMAC-SHA512 of raw body
        computed_sig = hmac.new(
            client_secret.encode('utf-8'),
            request.body,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(monnify_signature, computed_sig):
            logger.warning("Invalid Monnify Webhook Signature received.")
            return Response({"error": "Unauthorized signature"}, status=status.HTTP_400_BAD_REQUEST)

        payload = request.data
        event_type = payload.get("eventType")

        if event_type == "SUCCESSFUL_TRANSACTION":
            event_data = payload.get("eventData", {})
            payment_ref = event_data.get("paymentReference")
            amount = decimal.Decimal(str(event_data.get("amountPaid", 0)))
            customer_email = event_data.get("customer", {}).get("email")

            try:
                user = User.objects.get(email=customer_email)
                wallet = get_wallet(user)
                
                # Check for existing completed transaction reference to prevent double spending
                if Transaction.objects.filter(reference=payment_ref, status='success').exists():
                    return Response({"message": "Already processed"}, status=status.HTTP_200_OK)

                # Thread-safe wallet crediting
                wallet.credit_balance(amount)
                
                # Cashback: 1% on wallet funding
                cashback = round(amount * decimal.Decimal('0.01'), 2)
                wallet.cashback_balance += cashback
                wallet.save()

                # Log Transaction
                Transaction.objects.create(
                    user=user,
                    wallet=wallet,
                    type='fund',
                    amount=amount,
                    status='success',
                    reference=payment_ref,
                    details=f"Monnify Direct Virtual Account Funding"
                )

                # Send Notification
                Notification.objects.create(
                    user=user,
                    title='Wallet Funded via Transfer ✅',
                    message=f'Your virtual transfer of ₦{amount:,.2f} was successful. (Cashback: ₦{cashback:,.2f})',
                    icon='fund'
                )
                logger.info(f"Successfully processed Monnify webhook for user {user.username}, amount: {amount}")
                return Response({"status": "success"}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                logger.error(f"User with email {customer_email} not found in Monnify webhook.")
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "Unsupported event"}, status=status.HTTP_200_OK)


class PaystackWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Paystack webhook signature verification
        paystack_signature = request.headers.get('x-paystack-signature', '')
        client_secret = getattr(settings, 'PAYSTACK_SECRET_KEY', '')

        # Calculate HMAC-SHA512 of raw body
        computed_sig = hmac.new(
            client_secret.encode('utf-8'),
            request.body,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(paystack_signature, computed_sig):
            logger.warning("Invalid Paystack Webhook Signature received.")
            return Response({"error": "Unauthorized signature"}, status=status.HTTP_400_BAD_REQUEST)

        payload = request.data
        event = payload.get("event")

        if event == "charge.success":
            data = payload.get("data", {})
            ref = data.get("reference")
            # Paystack sends amount in Kobo
            amount = decimal.Decimal(str(data.get("amount", 0))) / 100
            customer_email = data.get("customer", {}).get("email")

            try:
                user = User.objects.get(email=customer_email)
                wallet = get_wallet(user)

                if Transaction.objects.filter(reference=ref, status='success').exists():
                    return Response({"message": "Already processed"}, status=status.HTTP_200_OK)

                wallet.credit_balance(amount)
                
                # Cashback: 1% on wallet funding
                cashback = round(amount * decimal.Decimal('0.01'), 2)
                wallet.cashback_balance += cashback
                wallet.save()

                Transaction.objects.create(
                    user=user,
                    wallet=wallet,
                    type='fund',
                    amount=amount,
                    status='success',
                    reference=ref,
                    details=f"Paystack Webhook Funding"
                )

                Notification.objects.create(
                    user=user,
                    title='Wallet Funded via Paystack ✅',
                    message=f'Your card payment of ₦{amount:,.2f} was successful. (Cashback: ₦{cashback:,.2f})',
                    icon='fund'
                )
                logger.info(f"Successfully processed Paystack webhook for user {user.username}, amount: {amount}")
                return Response({"status": "success"}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                logger.error(f"User with email {customer_email} not found in Paystack webhook.")
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"message": "Unsupported event"}, status=status.HTTP_200_OK)
