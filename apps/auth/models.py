import random
import string
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('reseller', 'Reseller'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_users')
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)

    def add_xp(self, amount):
        self.xp += amount
        new_level = (self.xp // 100) + 1
        if new_level > self.level:
            self.level = new_level
            return True  # Level up!
        return False

    def __str__(self):
        return f"{self.user.username}'s Profile"

def generate_referral_code():
    while True:
        code = 'PV-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Profile.objects.filter(referral_code=code).exists():
            return code

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        ref_code = generate_referral_code()
        Profile.objects.get_or_create(user=instance, defaults={'referral_code': ref_code})

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        ref_code = generate_referral_code()
        Profile.objects.get_or_create(user=instance, defaults={'referral_code': ref_code})
