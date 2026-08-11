from datetime import timedelta
from django.utils import timezone
from apps.billing.models import SubscriptionHistory, Payment
from apps.billing.asaas import AsaasSubscription, AsaasPayment


def activate_subscription(subscription):
    subscription.status = "ACTIVE"
    subscription.save()

    SubscriptionHistory.objects.create(
        subscription=subscription,
        plan=subscription.plan,
        status="ACTIVE",
    )


def deactivate_subscription(subscription):
    for payment in Payment.objects.filter(subscription=subscription, status="PENDING"):
        try:
            AsaasPayment().delete_payment(payment_id=payment.payment_id)
        except Exception:
            pass

    first_payment = Payment.objects.filter(subscription=subscription).order_by("created_at").first()
    if (
        first_payment and
        first_payment.status in ["CONFIRMED", "RECEIVED"] and
        first_payment.paid_at and
        first_payment.paid_at >= timezone.localdate() - timedelta(days=subscription.plan.refund_period)
    ):
        try:
            AsaasPayment().refund_payment(payment_id=first_payment.payment_id)
        except Exception:
            pass

    if subscription.billing_type == "PIX":
        try:
            AsaasSubscription().delete_pix_subscription(pix_authorization_id=subscription.pix_authorization_id)
        except Exception:
            pass

    subscription.pix_authorization_id = None
    subscription.pix_conciliation_identifier = None
    subscription.credit_card_token = None
    subscription.status = "INACTIVE"
    subscription.next_due = None
    subscription.save()

    SubscriptionHistory.objects.create(
        subscription=subscription,
        plan=subscription.plan,
        status="INACTIVE",
    )
