import json
from datetime import datetime, timedelta
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
from apps.account.models import User
from apps.payment.serializers import SubscriptionSignSerializer, SubscriptionRenewSerializer
from apps.payment.asaas import AsaasCustomer, AsaasCreditCardSubscription, AsaasPixSubscription, AsaasPayment
from apps.payment.models import Plan, Customer, Subscription, SubscriptionStatusHistory, SubscriptionPlanHistory, Payment, Webhook


class SubscriptionPolling(APIView):

    def get(self, request):
        if (
            Subscription.objects
            .filter(
                customer__customer_id=request.session.get("customer_id"),
                status="ACTIVE",
            ).exists()
        ):
            del request.session["customer_id"]
            return Response(status=status.HTTP_200_OK)
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
            first_name, separator, last_name = data["full_name"].partition(" ")
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=data["email"],
                password=data["password"],
                phone_number=data["phone_number"],
                birth_date=data["birth_date"],
                postal_code=asaas_customer["postalCode"],
                state=asaas_customer["state"],
                city=asaas_customer["cityName"],
                neighborhood=asaas_customer["province"],
                street=asaas_customer["address"],
                address_number=asaas_customer["addressNumber"],
                # is_active=False,
            )
        except Exception:
            AsaasCustomer().delete_customer(customer_id=asaas_customer["id"])
            return Response({
                "detail": "Este e-mail já está cadastrado, acesse a conta e renove sua assinatura",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        # request.session["customer_id"] = asaas_customer["id"]

        if data["billing_type"] == "PIX":
            try:
                asaas_subscription = AsaasPixSubscription().create_subscription(
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
                subscription_id=asaas_subscription["id"],
                customer=customer,
                plan=data["plan"],
                next_due=asaas_subscription["startDate"],
            )

            group, created = Group.objects.get_or_create(name="Clientes")
            user.groups.add(group)

            return Response({
                "customer_id": asaas_customer["id"],
                "encoded_image": asaas_subscription["encodedImage"],
            }, status=status.HTTP_200_OK)

        elif data["billing_type"] == "CREDIT_CARD":
            try:
                asaas_subscription = AsaasCreditCardSubscription().create_subscription(
                    customer_id=asaas_customer["id"],
                    value=data["plan"].value,
                    cycle=data["plan"].cycle,
                    next_due_date=timezone.localdate().isoformat(),
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
                    "detail": "Cartão de crédito inválido",
                    "detail_type": "error",
                }, status=status.HTTP_400_BAD_REQUEST)

            customer = Customer.objects.create(
                customer_id=asaas_customer["id"],
                user=user,
            )

            Subscription.objects.create(
                subscription_id=asaas_subscription["id"],
                customer=customer,
                plan=data["plan"],
                next_due=asaas_subscription["nextDueDate"],
            )

            group, created = Group.objects.get_or_create(name="Clientes")
            user.groups.add(group)

            return Response({
                "customer_id": asaas_customer["id"],
            }, status=status.HTTP_200_OK)


class SubscriptionPlanChange(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            plan = Plan.objects.get(id=request.data.get("plan_id"), active=True)
        except Plan.DoesNotExist:
            return Response({
                "detail": "Esse plano não existe ou está inativo no momento",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            subscription = (
                Subscription.objects
                .select_related("plan")
                .get(customer__user=request.user, status="ACTIVE")
            )
        except Subscription.DoesNotExist:
            return Response({
                "detail": "Você não possui uma assinatura ativa",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        if subscription.plan == plan:
            return Response({
                "detail": "Você já está utilizando este plano",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        if subscription.subscription_plan_histories.filter(status="PENDING").exists():
            return Response({
                "detail": "Você já possui uma troca de plano pendente",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        if subscription.plan.cycle != plan.cycle:
            return Response({
                "detail": "Você não pode alterar para um plano com ciclo diferente",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        AsaasCreditCardSubscription().update_subscription(
            subscription_id=subscription.subscription_id,
            value=plan.value,
            description=plan.name,
            updatePendingPayments=True,
        )

        SubscriptionPlanHistory.objects.create(
            subscription=subscription,
            old_plan=subscription.plan,
            new_plan=plan,
            status="PENDING",
        )

        return Response({
            "detail": "Seu plano será alterado na próxima cobrança",
            "detail_type": "success",
        }, status=status.HTTP_200_OK)


class SubscriptionRenew(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SubscriptionRenewSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            subscription = (
                Subscription.objects
                .select_related("customer")
                .get(customer__user=request.user, status__in=["INACTIVE", "EXPIRED"])
            )
        except Subscription.DoesNotExist:
            return Response({
                "detail": "Sua assinatura já está ativa",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            AsaasPayment().create_payment(
                customer_id=subscription.customer.customer_id,
                value=data["value"],
                due_date=timezone.localdate().isoformat(),
                description=data["name"],
                external_reference=subscription.subscription_id,
                credit_card={
                    "holderName": data["holder_name"],
                    "number": data["number"],
                    "expiryMonth": data["expiry_date"][0],
                    "expiryYear": data["expiry_date"][1],
                    "ccv": data["ccv"],
                },
                credit_card_holder_info={
                    "name": request.user.get_full_name(),
                    "email": request.user.email,
                    "mobilePhone": request.user.phone_number,
                    "cpfCnpj": data["cpf"],
                    "postalCode": request.user.postal_code,
                    "addressNumber": request.user.address_number,
                },
            )
        except:
            return Response({
                "detail": "Cartão de crédito inválido",
                "detail_type": "error",
            }, status=status.HTTP_400_BAD_REQUEST)

        AsaasCreditCardSubscription().update_subscription(
            subscription_id=subscription.subscription_id,
            status="ACTIVE",
            value=data["value"],
            next_due_date=(timezone.localdate() + timedelta(days=30)).isoformat(),
            description=data["name"],
        )

        AsaasCreditCardSubscription().update_credit_card(
            subscription_id=subscription.subscription_id,
            credit_card={
                "holderName": data["holder_name"],
                "number": data["number"],
                "expiryMonth": data["expiry_date"][0],
                "expiryYear": data["expiry_date"][1],
                "ccv": data["ccv"],
            },
            credit_card_holder_info={
                "name": request.user.get_full_name(),
                "email": request.user.email,
                "mobilePhone": request.user.phone_number,
                "cpfCnpj": data["cpf"],
                "postalCode": request.user.postal_code,
                "addressNumber": request.user.address_number,
            },
        )

        subscription.plan = data["plan"]
        subscription.save()

        return Response({
            "detail": "Assinatura renovada",
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

        AsaasCreditCardSubscription().update_subscription(
            subscription_id=subscription.subscription_id,
            status="INACTIVE",
        )

        SubscriptionPlanHistory.objects.filter(
            subscription=subscription,
            status="PENDING",
        ).delete()

        if pending_payments := Payment.objects.filter(subscription=subscription, status="PENDING"):
            for payment in pending_payments:
                AsaasPayment().delete_payment(payment_id=payment.payment_id)

        if first_payment := (
            Payment.objects
            .filter(subscription=subscription, status="CONFIRMED")
            .last()
        ):
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
                webhook, created = Webhook.objects.get_or_create(
                    event_id=payload.get("id"),
                    defaults={
                        "subscription": Subscription.objects.get(
                            subscription_id=(
                                payload.get("subscription", {}).get("id") or
                                payload.get("payment", {}).get("subscription") or
                                payload.get("payment", {}).get("externalReference")
                            )
                        ),
                        "payload": payload,
                    },
                )
                if not created:
                    return Response(status=status.HTTP_200_OK)

                if event in ["SUBSCRIPTION_CREATED", "SUBSCRIPTION_UPDATED", "SUBSCRIPTION_INACTIVATED"]:
                    data = payload.get("subscription")
                    old_status = Subscription.objects.filter(subscription_id=data.get("id")).values_list("status", flat=True).first()

                    subscription, created = Subscription.objects.update_or_create(
                        subscription_id=data.get("id"),
                        defaults={
                            "status": data.get("status"),
                            "next_due": (
                                None
                                if data.get("status") == "INACTIVE"
                                else datetime.strptime(data.get("nextDueDate"), "%Y-%m-%d").date()
                            ),
                        },
                    )

                    if created or old_status != data.get("status"):
                        SubscriptionStatusHistory.objects.create(
                            subscription=subscription,
                            status=data.get("status"),
                        )

                elif event == "SUBSCRIPTION_DELETED":
                    if subscription := Subscription.objects.filter(subscription_id=payload.get("subscription").get("id")).first():
                        subscription.delete()

                elif event in ["PAYMENT_CREATED", "PAYMENT_UPDATED", "PAYMENT_CONFIRMED", "PAYMENT_RECEIVED", "PAYMENT_OVERDUE", "PAYMENT_REFUNDED"]:
                    data = payload.get("payment")
                    subscription = Subscription.objects.get(subscription_id=data.get("subscription") or data.get("externalReference"))

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
                        if pending_history := subscription.subscription_plan_histories.filter(status="PENDING").first():
                            subscription.plan = pending_history.new_plan
                            subscription.save()
                            pending_history.status = "CONFIRMED"
                            pending_history.save()

                    if event == "PAYMENT_OVERDUE":
                        AsaasCreditCardSubscription().update_subscription(
                            subscription_id=subscription.subscription_id,
                            status="INACTIVE",
                        )

                        SubscriptionPlanHistory.objects.filter(
                            subscription=subscription,
                            status="PENDING",
                        ).delete()

                        if pending_payments := Payment.objects.filter(subscription=subscription, status="PENDING"):
                            for payment in pending_payments:
                                AsaasPayment().delete_payment(payment_id=payment.payment_id)

                elif event == "PAYMENT_DELETED":
                    if payment := Payment.objects.filter(payment_id=payload.get("payment").get("id")).first():
                        payment.delete()
        except Exception as error:
            return Response({"error": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_200_OK)
