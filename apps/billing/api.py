import json
from uuid import uuid4
from datetime import datetime
from dateutil.relativedelta import relativedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.core import signing
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from apps.account.models import User
from apps.billing.asaas import AsaasCustomer, AsaasSubscription
from apps.billing.serializers import SubscriptionSignSerializer
from apps.billing.utils import activate_subscription, deactivate_subscription
from apps.billing.models import Customer, Subscription, SubscriptionHistory, Payment, Webhook


CYCLE_DELTA = {
    "WEEKLY": relativedelta(weeks=1),
    "MONTHLY": relativedelta(months=1),
    "QUARTERLY": relativedelta(months=3),
    "SEMIANNUALLY": relativedelta(months=6),
    "ANNUALLY": relativedelta(years=1),
}


class SubscriptionPolling(APIView):

    def get(self, request):
        try:
            data = signing.loads(
                request.query_params.get("token"),
                salt="subscription-polling",
                max_age=3600,
            )
        except signing.BadSignature:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if (
            Subscription.objects
            .filter(
                customer__customer_id=data["customer_id"],
                status="ACTIVE",
            )
            .exists()
        ):
            return Response({
                "detail": "Assinatura finalizada",
                "detail_type": "success",
            }, status=status.HTTP_200_OK)

        return Response(status=status.HTTP_404_NOT_FOUND)


class SubscriptionSign(APIView):

    def post(self, request):
        serializer = SubscriptionSignSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            asaas_customer = AsaasCustomer().create_customer(
                name=data["full_name"],
                cpf_cnpj=data["cpf"],
                email=data["email"],
                mobile_phone=data["phone_number"],
                postal_code=data["postal_code"],
                address_number=data["address_number"],
            )
        except Exception:
            return Response({
                "detail": "CPF ou CEP inválido",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            contract_id = uuid4().hex
            first_name, separator, last_name = data["full_name"].partition(" ")
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=data["email"],
                password=data["password"],
            )
        except Exception:
            AsaasCustomer().delete_customer(customer_id=asaas_customer["id"])
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if data["billing_type"] == "PIX":
            try:
                asaas_subscription = AsaasSubscription().create_pix_subscription(
                    contract_id=contract_id,
                    customer_id=asaas_customer["id"],
                    first_value=data["plan"].value,
                    recurring_value=data["plan"].value,
                    cycle=data["plan"].cycle,
                    due_date=timezone.localdate().isoformat(),
                    description=data["plan"].name,
                )
            except Exception:
                user.delete()
                AsaasCustomer().delete_customer(customer_id=asaas_customer["id"])
                return Response({
                    "detail": "Dados de pagamento inválidos",
                    "detail_type": "error",
                }, status=status.HTTP_400_BAD_REQUEST)

        elif data["billing_type"] == "CREDIT_CARD":
            try:
                asaas_payment = AsaasSubscription().create_credit_card_subscription(
                    customer_id=asaas_customer["id"],
                    billing_type=data["billing_type"],
                    value=data["plan"].value,
                    due_date=timezone.localdate().isoformat(),
                    description=data["plan"].name,
                    credit_card={
                        "holderName": data["holder_name"],
                        "number": data["number"],
                        "expiryMonth": data["expiry_date"][0],
                        "expiryYear": data["expiry_date"][1],
                        "ccv": data["ccv"],
                    },
                    credit_card_holder_info={
                        "name": data["full_name"],
                        "email": data["email"],
                        "mobilePhone": data["phone_number"],
                        "cpfCnpj": data["cpf"],
                        "postalCode": data["postal_code"],
                        "addressNumber": data["address_number"],
                    },
                )
            except Exception:
                user.delete()
                AsaasCustomer().delete_customer(customer_id=asaas_customer["id"])
                return Response({
                    "detail": "Dados de pagamento inválidos",
                    "detail_type": "error",
                }, status=status.HTTP_400_BAD_REQUEST)

        customer = Customer.objects.create(
            customer_id=asaas_customer["id"],
            user=user,
        )

        subscription = Subscription.objects.create(
            subscription_id=contract_id,
            pix_conciliation_identifier=asaas_payment["immediateQrCode"]["conciliationIdentifier"] if data["billing_type"] == "PIX" else None,
            pix_authorization_id=asaas_payment["id"] if data["billing_type"] == "PIX" else None,
            credit_card_token=asaas_payment["creditCard"]["creditCardToken"] if data["billing_type"] == "CREDIT_CARD" else None,
            customer=customer,
            plan=data["plan"],
            billing_type=data["billing_type"],
            status="ACTIVE" if data["billing_type"] == "CREDIT_CARD" else "INACTIVE",
        )

        if data["billing_type"] == "PIX":
            token = signing.dumps(
                {
                    "customer_id": customer.customer_id,
                },
                salt="subscription-polling",
            )

            return Response({
                "token": token,
                "payload": asaas_subscription["payload"],
                "encoded_image": asaas_subscription["encodedImage"],
            }, status=status.HTTP_200_OK)

        elif data["billing_type"] == "CREDIT_CARD":
            SubscriptionHistory.objects.create(
                subscription=subscription,
                plan=subscription.plan,
                status="ACTIVE",
            )

            return Response({
                "detail": "Assinatura finalizada",
                "detail_type": "success",
            }, status=status.HTTP_200_OK)


class SubscriptionCancel(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            subscription = (
                Subscription.objects
                .select_related("plan")
                .get(customer__user=request.user, status="ACTIVE")
            )
        except Subscription.DoesNotExist:
            return Response({
                "detail": "Nenhuma assinatura ativa encontrada",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        deactivate_subscription(subscription)

        return Response({
            "detail": "Assinatura cancelada",
            "detail_type": "success",
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name="dispatch")
class AsaasWebhook(APIView):

    def post(self, request):
        if request.headers.get("asaas-access-token") != settings.ASAAS_ACCESS_TOKEN:
            return Response(status=status.HTTP_200_OK)

        try:
            payload = json.loads(request.body.decode())
            event = payload.get("event")

            with transaction.atomic():
                customer_id = (
                    payload.get("payment", {}).get("customer") or
                    payload.get("authorization", {}).get("customerId") or
                    payload.get("paymentInstruction", {}).get("authorization", {}).get("customerId")
                )
                conciliation_id = (
                    payload.get("payment", {}).get("pixQrCodeId") or
                    payload.get("paymentInstruction", {}).get("conciliationIdentifier")
                )

                filters = Q()
                if customer_id:
                    filters |= Q(customer__customer_id=customer_id)
                if conciliation_id:
                    filters |= Q(pix_conciliation_identifier=conciliation_id)

                subscription = Subscription.objects.filter(filters).first() if filters else None
                if not subscription:
                    customer = Customer.objects.filter(customer_id=customer_id).first()

                webhook, created = Webhook.objects.get_or_create(
                    webhook_id=payload.get("id"),
                    defaults={
                        "subscription": subscription,
                        "customer": subscription.customer if subscription else customer,
                        "event": event,
                        "payload": payload,
                    },
                )
                if not created:
                    return Response(status=status.HTTP_200_OK)

                if event in [
                    "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_ACTIVATED", "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_CANCELLED", "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_EXPIRED",
                    "PIX_AUTOMATIC_RECURRING_PAYMENT_INSTRUCTION_REFUSED",
                ]:
                    if event == "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_ACTIVATED":
                        activate_subscription(subscription)
                    else:
                        deactivate_subscription(subscription)

                elif event in [
                    "PAYMENT_CREATED", "PAYMENT_CONFIRMED", "PAYMENT_RECEIVED",
                    "PAYMENT_UPDATED", "PAYMENT_OVERDUE", "PAYMENT_REFUNDED",
                ]:
                    data = payload.get("payment")

                    Payment.objects.update_or_create(
                        payment_id=data.get("id"),
                        defaults={
                            "subscription": subscription,
                            "customer": subscription.customer if subscription else customer,
                            "value": data.get("value"),
                            "billing_type": data.get("billingType"),
                            "status": data.get("status"),
                            "paid_at": data.get("clientPaymentDate"),
                            "due_date": data.get("dueDate"),
                        },
                    )

                    if subscription and (
                        event == "PAYMENT_CONFIRMED" and data.get("billingType") == "CREDIT_CARD" or
                        event == "PAYMENT_RECEIVED" and data.get("billingType") == "PIX"
                    ):
                        subscription.next_due = datetime.strptime(data.get("dueDate"), "%Y-%m-%d").date() + CYCLE_DELTA[subscription.plan.cycle]
                        subscription.save()

                elif event == "PAYMENT_DELETED":
                    Payment.objects.filter(payment_id=payload.get("payment").get("id")).delete()
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_200_OK)
