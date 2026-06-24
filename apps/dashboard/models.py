import uuid
from django.db import models, transaction
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password, check_password

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    cashback_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pin = models.CharField(max_length=128, blank=True, null=True)  # Salted and hashed pin
    updated_at = models.DateTimeField(auto_now=True)

    def set_pin(self, raw_pin):
        self.pin = make_password(str(raw_pin))
        self.save()

    def verify_pin(self, raw_pin):
        if not self.pin:
            return False
        return check_password(str(raw_pin), self.pin)

    def deduct_balance(self, amount, pin_provided=None):
        """Thread-safe balance deduction using row-level locking."""
        with transaction.atomic():
            locked_wallet = Wallet.objects.select_for_update().get(id=self.id)
            if pin_provided and not locked_wallet.verify_pin(pin_provided):
                raise ValueError("Invalid transaction PIN.")
            if locked_wallet.balance < amount:
                raise ValueError("Insufficient wallet balance.")
            locked_wallet.balance -= amount
            locked_wallet.save()
            self.balance = locked_wallet.balance
            return locked_wallet

    def credit_balance(self, amount):
        """Thread-safe balance crediting using row-level locking."""
        with transaction.atomic():
            locked_wallet = Wallet.objects.select_for_update().get(id=self.id)
            locked_wallet.balance += amount
            locked_wallet.save()
            self.balance = locked_wallet.balance
            return locked_wallet

    def __str__(self):
        return f"{self.user.username}'s Wallet (Bal: ₦{self.balance})"

class Transaction(models.Model):
    TYPE_CHOICES = (
        ('fund', 'Wallet Funding'),
        ('purchase', 'Service Purchase'),
        ('refund', 'Failed Order Refund'),
        ('commission', 'Referral Commission'),
        ('cashback_redeem', 'Cashback Redemption'),
    )
    SERVICE_CHOICES = (
        ('airtime', 'Airtime'),
        ('data', 'Data Subscription'),
        ('electricity', 'Electricity Bill'),
        ('tv', 'TV Subscription'),
        ('exam', 'Exam Pin'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_transactions')
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='dashboard_transactions')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    service = models.CharField(max_length=20, choices=SERVICE_CHOICES, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, unique=True)
    details = models.TextField(blank=True, default='')
    vendor_response_log = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} | {self.get_type_display()} | ₦{self.amount} | {self.status}"

class DataPlan(models.Model):
    NETWORK_CHOICES = (
        ('MTN', 'MTN'),
        ('Airtel', 'Airtel'),
        ('Glo', 'Glo'),
        ('9mobile', '9mobile'),
    )
    network = models.CharField(max_length=20, choices=NETWORK_CHOICES)
    name = models.CharField(max_length=100)
    volume = models.CharField(max_length=30)
    validity = models.CharField(max_length=30)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    plan_code = models.CharField(max_length=50, default='')
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['network', 'price']

    def __str__(self):
        return f"{self.network} – {self.name} ({self.volume}) ₦{self.price}"

class Subscription(models.Model):
    SCHEDULE_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_subscriptions')
    plan = models.ForeignKey(DataPlan, on_delete=models.CASCADE, null=True, blank=True)
    service_type = models.CharField(max_length=20, default='data')
    phone_number = models.CharField(max_length=20)
    schedule = models.CharField(max_length=20, choices=SCHEDULE_CHOICES, default='monthly')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    next_run = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} | {self.service_type} | {self.schedule}"

class SupportTicket(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_tickets')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.subject} – {self.user.username}"

class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    icon = models.CharField(max_length=50, default='🏅')
    xp_required = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class UserBadge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-unlocked_at']

    def __str__(self):
        return f"{self.user.username} – {self.badge.name}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    icon = models.CharField(max_length=50, default='🔔')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} – {self.title}"

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_wallet(sender, instance, **kwargs):
    if hasattr(instance, 'wallet'):
        instance.wallet.save()
    else:
        Wallet.objects.get_or_create(user=instance)
