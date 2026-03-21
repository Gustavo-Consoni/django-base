from django.urls import path
from apps.payment import views, api


urlpatterns = [
    path("assinar", views.SubscriptionCheckout.as_view(), name="subscription_checkout"),
    path("assinatura-finalizada", views.SubscriptionCompleted.as_view(), name="subscription_completed"),

    path("api/subscription/polling", api.SubscriptionPolling.as_view(), name="subscription_polling"),
    path("api/subscription/sign", api.SubscriptionSign.as_view(), name="subscription_sign"),
    path("api/subscription/plan/change", api.SubscriptionPlanChange.as_view(), name="subscription_plan_change"),
    path("api/subscription/renew", api.SubscriptionRenew.as_view(), name="subscription_renew"),
    path("api/subscription/cancel", api.SubscriptionCancel.as_view(), name="subscription_cancel"),
    path("api/asaas/webhook", api.AsaasWebhook.as_view(), name="asaas_webhook"),
]
