import uuid
import decimal
import logging
from celery import shared_task
from django.db import transaction
from django.contrib.auth.models import User
from apps.dashboard.models import Wallet, Transaction, Badge, UserBadge, Notification
from apps.dashboard.services import BigiSubClient

logger = logging.getLogger(__name__)

@shared_task
def process_vtu_purchase_task(transaction_id_str):
    """
    Celery background task to process a pending VTU transaction via BigiSub API.
    Handles row-locking and automatic refund on API failure.
    """
    logger.info(f"Background task started for transaction: {transaction_id_str}")
    
    # We lock the transaction to prevent concurrent modifications
    with transaction.atomic():
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id_str)
        except Transaction.DoesNotExist:
            logger.error(f"Transaction {transaction_id_str} not found in database.")
            return False

        if txn.status != 'pending':
            logger.warning(f"Transaction {txn.id} is already in state '{txn.status}'. Skipping task.")
            return False

        wallet = txn.wallet
        user = txn.user
        
        # Initialize BigiSub client
        client = BigiSubClient()
        
        # Call appropriate service type
        if txn.service == 'data':
            # Extract details to find plan code (passed in transaction details or we can search data plans)
            # In a real app we'd pass the plan code. We can extract it from the details or look up DataPlan.
            plan_code = "sme_1gb"  # fallback default
            # Let's search if the details mention a plan_code or retrieve from plan
            plan_code_match = [part for part in txn.details.split() if part.startswith("CODE:")]
            if plan_code_match:
                plan_code = plan_code_match[0].replace("CODE:", "")
            response = client.purchase_data(txn.details, txn.details, plan_code)
        else:
            # Airtime or other services
            response = client.purchase_airtime(txn.details, txn.details, txn.amount)

        # Log vendor response
        txn.vendor_response_log = response
        
        if response.get("status") == "success":
            logger.info(f"BigiSub API call succeeded for transaction: {txn.id}")
            txn.status = 'success'
            txn.save()
            
            # Award cashback (0.5% standard rebate)
            cashback = round(txn.amount * decimal.Decimal('0.005'), 2)
            with transaction.atomic():
                locked_wallet = Wallet.objects.select_for_update().get(id=wallet.id)
                locked_wallet.cashback_balance += cashback
                locked_wallet.save()

            # Award XP & handle badges (stored in profile, which is in apps.auth.models)
            try:
                profile = user.profile
                profile.add_xp(10 if txn.service == 'data' else 5)
                profile.save()
                
                # Check First Top-Up Badge
                success_purchases = Transaction.objects.filter(user=user, type='purchase', status='success').count()
                if success_purchases == 1:
                    try:
                        badge = Badge.objects.get(name='First Top-Up')
                        UserBadge.objects.get_or_create(user=user, badge=badge)
                    except Badge.DoesNotExist:
                        pass
            except Exception as e:
                logger.error(f"Failed to award user XP/badge: {str(e)}")

            # Send Notification
            Notification.objects.create(
                user=user,
                title='Transaction Successful ✅',
                message=f'Your purchase of ₦{txn.amount:,.2f} ({txn.get_service_display()}) was processed successfully!',
                icon='✅'
            )
            return True
        else:
            logger.error(f"BigiSub API call failed for transaction {txn.id}: {response.get('message')}")
            txn.status = 'failed'
            txn.save()
            
            # Refund: Credit client balance safely
            with transaction.atomic():
                locked_wallet = Wallet.objects.select_for_update().get(id=wallet.id)
                locked_wallet.balance += txn.amount
                locked_wallet.save()

            # Log refund transaction record
            ref_id = 'REF-' + str(uuid.uuid4()).replace('-', '')[:16].upper()
            Transaction.objects.create(
                user=user,
                wallet=wallet,
                type='refund',
                amount=txn.amount,
                status='success',
                reference=ref_id,
                details=f"Refund for failed transaction ref: {txn.reference}"
            )

            # Send Notification
            Notification.objects.create(
                user=user,
                title='Transaction Failed – Refunded ⚠️',
                message=f'Failed to process your {txn.get_service_display()} top-up. ₦{txn.amount:,.2f} has been refunded to your wallet.',
                icon='⚠️'
            )
            return False
