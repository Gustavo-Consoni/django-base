from time import sleep
from celery import shared_task
from datetime import timedelta
from sentry_sdk import capture_exception
from django.db.models import Q
from django.utils import timezone
from apps.billing.asaas import AsaasPayment
from apps.billing.models import Subscription, Payment
from apps.billing.utils import deactivate_subscription


@shared_task
def create_recurring_payments():
    today = timezone.localdate()

    subscriptions = (
        Subscription.objects
        .filter(
            Q(billing_type="PIX", next_due__range=(today + timedelta(days=2), today + timedelta(days=8)), pix_authorization_id__isnull=False) |
            Q(billing_type="CREDIT_CARD", next_due__lte=today, credit_card_token__isnull=False),
            status="ACTIVE",
        )
        .select_related("customer", "plan")
    )

    for subscription in subscriptions:
        if Payment.objects.filter(subscription=subscription, due_date=subscription.next_due).exists():
            continue

        try:
            if subscription.billing_type == "PIX":
                AsaasPayment().create_payment(
                    customer_id=subscription.customer.customer_id,
                    billing_type=subscription.billing_type,
                    value=subscription.plan.value,
                    due_date=subscription.next_due.isoformat(),
                    description=subscription.plan.name,
                    external_reference=subscription.subscription_id,
                    pix_authorization_id=subscription.pix_authorization_id,
                )
            elif subscription.billing_type == "CREDIT_CARD":
                AsaasPayment().create_payment(
                    customer_id=subscription.customer.customer_id,
                    billing_type=subscription.billing_type,
                    value=subscription.plan.value,
                    due_date=subscription.next_due.isoformat(),
                    description=subscription.plan.name,
                    external_reference=subscription.subscription_id,
                    credit_card_token=subscription.credit_card_token,
                )
        except Exception as error:
            deactivate_subscription(subscription)
            capture_exception(error)

        sleep(0.5)
