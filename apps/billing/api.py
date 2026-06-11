import json
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import Group
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from apps.account.models import User, Company, Employee
from apps.billing.asaas import AsaasCustomer, AsaasPayment
from apps.billing.serializers import SubscriptionCompanySignSerializer, SubscriptionEmployeeSignSerializer
from apps.billing.models import Subscription, SubscriptionStatusHistory, SubscriptionPlanHistory, Customer, Payment, Webhook


CYCLE_DELTA = {
    "MONTHLY": relativedelta(months=1),
    "QUARTERLY": relativedelta(months=3),
    "SEMIANNUALLY": relativedelta(months=6),
    "ANNUALLY": relativedelta(years=1),
}


class SubscriptionPolling(APIView):

    def get(self, request):
        if (
            Subscription.objects
            .filter(
                customer__customer_id=request.query_params.get("customer_id"),
                status="ACTIVE",
            )
            .exists()
        ):
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_404_NOT_FOUND)


class SubscriptionCompanySign(APIView):

    def post(self, request):
        serializer = SubscriptionCompanySignSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            asaas_customer = AsaasCustomer().create_customer(
                name=data["full_name"],
                email=data["email"],
                cpf_cnpj=data["cnpj"],
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
            first_name, separator, last_name = data["full_name"].partition(" ")
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=data["email"],
                password=data["password"],
                user_type="COMPANY",
            )
        except Exception:
            AsaasCustomer().delete_customer(customer_id=asaas_customer["id"])
            return Response(status=status.HTTP_400_BAD_REQUEST)

        Customer.objects.create(
            customer_id=asaas_customer["id"],
            user=user,
        )

        Company.objects.create(
            user=user,
            cnpj=data["cnpj"],
            fantasy_name=data["fantasy_name"],
            company_category=data["company_category"],
            phone_number=data["phone_number"],
            postal_code=asaas_customer["postalCode"],
            state=asaas_customer["state"],
            city=asaas_customer["cityName"],
            neighborhood=asaas_customer["province"],
            street=asaas_customer["address"],
            address_number=asaas_customer["addressNumber"],
            complement=asaas_customer["complement"],
        )

        company_group, _ = Group.objects.get_or_create(name="company")
        company_group.user_set.add(user)

        return Response(status=status.HTTP_200_OK)


class SubscriptionEmployeeSign(APIView):

    def post(self, request):
        serializer = SubscriptionEmployeeSignSerializer(data=request.data)
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
            first_name, separator, last_name = data["full_name"].partition(" ")
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=data["email"],
                password=data["password"],
                user_type="EMPLOYEE",
            )
        except Exception:
            AsaasCustomer().delete_customer(customer_id=asaas_customer["id"])
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            asaas_subscription = AsaasPayment().create_pix_authorization(
                customer_id=asaas_customer["id"],
                value=data["plan"].value,
                cycle=data["plan"].cycle,
                next_due_date=timezone.localdate().isoformat(),
                description=data["plan"].name,
            )
        except Exception:
            user.delete()
            AsaasCustomer().delete_customer(customer_id=asaas_customer["id"])
            return Response({
                "detail": "Dados do PIX inválidos",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        customer = Customer.objects.create(
            customer_id=asaas_customer["id"],
            user=user,
        )

        Subscription.objects.create(
            subscription_id=asaas_subscription["contractId"],
            authorization_id=asaas_subscription["id"],
            customer=customer,
            plan=data["plan"],
            billing_type="PIX",
            status="INACTIVE",
            next_due=timezone.now().date(),
        )

        Employee.objects.create(
            user=user,
            cpf=data["cpf"],
            phone_number=data["phone_number"],
            birth_date=data["birth_date"],
            gender=data["gender"],
            marital_status=data["marital_status"],
            postal_code=asaas_customer["postalCode"],
            state=asaas_customer["state"],
            city=asaas_customer["cityName"],
            neighborhood=asaas_customer["province"],
            street=asaas_customer["address"],
            address_number=asaas_customer["addressNumber"],
        )

        employee_group, _ = Group.objects.get_or_create(name="employee")
        employee_group.user_set.add(user)

        return Response({
            "customer_id": asaas_customer["id"],
            "payload": asaas_subscription["payload"],
            "encoded_image": asaas_subscription["encodedImage"],
        }, status=status.HTTP_200_OK)


class SubscriptionRenew(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pass


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

        AsaasPayment().delete_pix_authorization(
            authorization_id=subscription.authorization_id,
        )

        SubscriptionPlanHistory.objects.filter(
            subscription=subscription,
            status="PENDING",
        ).delete()

        if pending_payments := Payment.objects.filter(subscription=subscription, status="PENDING"):
            for payment in pending_payments:
                AsaasPayment().delete_payment(payment_id=payment.payment_id)

        first_payment = Payment.objects.filter(subscription=subscription).first()
        if first_payment.paid_at >= timezone.localdate() - timedelta(days=subscription.plan.refund_period):
            AsaasPayment().refund_payment(payment_id=first_payment.payment_id)

        return Response({
            "detail": "Assinatura cancelada, você não receberá mais cobranças",
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
                subscription = Subscription.objects.get(
                    customer__customer_id=(
                        payload.get("payment", {}).get("customer") or
                        payload.get("authorization", {}).get("customerId") or
                        payload.get("paymentInstruction", {}).get("authorization", {}).get("customerId")
                    )
                )

                webhook, created = Webhook.objects.get_or_create(
                    event_id=payload.get("id"),
                    defaults={
                        "subscription": subscription,
                        "payload": payload,
                    },
                )
                if not created:
                    return Response(status=status.HTTP_200_OK)

                if event in [
                    "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_ACTIVATED", "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_CANCELLED",
                    "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_EXPIRED",
                ]:
                    if event == "PIX_AUTOMATIC_RECURRING_AUTHORIZATION_ACTIVATED":
                        new_status = "ACTIVE"
                    else:
                        new_status = "INACTIVE"
                        subscription.next_due = None

                        if pending_payments := Payment.objects.filter(subscription=subscription, status="PENDING"):
                            for payment in pending_payments:
                                AsaasPayment().delete_payment(payment_id=payment.payment_id)

                    subscription.status = new_status
                    subscription.save()

                    SubscriptionStatusHistory.objects.create(
                        subscription=subscription,
                        status=new_status,
                    )

                elif event in [
                    "PAYMENT_CREATED", "PAYMENT_CONFIRMED", "PAYMENT_RECEIVED",
                    "PAYMENT_UPDATED", "PAYMENT_OVERDUE", "PAYMENT_REFUNDED",
                ]:
                    data = payload.get("payment")

                    Payment.objects.update_or_create(
                        payment_id=data.get("id"),
                        defaults={
                            "subscription": subscription,
                            "value": data.get("value"),
                            "status": data.get("status"),
                            "paid_at": data.get("clientPaymentDate"),
                            "due_date": data.get("dueDate"),
                        },
                    )

                    if event == "PAYMENT_CONFIRMED":
                        subscription.next_due = subscription.next_due + CYCLE_DELTA[subscription.plan.cycle]
                        subscription.save()

                    elif event == "PAYMENT_OVERDUE":
                        subscription.status = "INACTIVE"
                        subscription.next_due = None
                        subscription.save()

                        if pending_payments := Payment.objects.filter(subscription=subscription, status="PENDING"):
                            for payment in pending_payments:
                                AsaasPayment().delete_payment(payment_id=payment.payment_id)

                elif event == "PAYMENT_DELETED":
                    if payment := Payment.objects.filter(payment_id=payload.get("payment").get("id")).first():
                        payment.delete()
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_200_OK)
