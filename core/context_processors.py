from django.conf import settings


def pwa(request):
    return {
        "vapid_public_key": settings.VAPID_PUBLIC_KEY,
    }
