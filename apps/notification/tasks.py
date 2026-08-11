import json
from pywebpush import webpush
from celery import shared_task
from django.conf import settings
from django.templatetags.static import static
from apps.notification.models import WebpushSubscription


@shared_task
def notify_user(user_id, title, body, url=None):
    if webpush_subscription := WebpushSubscription.objects.filter(user_id=user_id).first():
        try:
            webpush(
                subscription_info=webpush_subscription.as_dict(),
                data=json.dumps({
                    "icon": static("images/logo/descolada-com-fundo-192x192.png"),
                    "badge": static("images/logo/colada-sem-fundo-192x192.png"),
                    "title": title,
                    "body": body,
                    "data": {
                        "url": url,
                    },
                }),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": f"mailto:{settings.VAPID_EMAIL}",
                },
                ttl=86400,
            )
        except Exception as error:
            print(f"Erro ao enviar push: {error}")
