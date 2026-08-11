from django.db import models
from apps.account.models import User


class WebpushSubscription(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name="webpush_subscription", verbose_name="Usuário")
    endpoint   = models.TextField(unique=True)
    auth       = models.TextField()
    p256dh     = models.TextField()
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")

    def as_dict(self):
        return {
            "endpoint": self.endpoint,
            "keys": {
                "auth": self.auth,
                "p256dh": self.p256dh,
            }
        }

    def __str__(self):
        return self.user.get_full_name()

    class Meta:
        verbose_name = "assinatura webpush"
        verbose_name_plural = "assinaturas webpush"
