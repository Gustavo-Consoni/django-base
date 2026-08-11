from django.urls import path
from apps.notification import api


urlpatterns = [
    path("webpush/subscribe", api.WebpushSubscribe.as_view(), name="webpush_subscribe"),
    path("webpush/resubscribe", api.WebpushResubscribe.as_view(), name="webpush_resubscribe"),
    path("webpush/unsubscribe", api.WebpushUnsubscribe.as_view(), name="webpush_unsubscribe"),
]
