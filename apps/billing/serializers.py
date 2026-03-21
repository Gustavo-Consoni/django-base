import re
from rest_framework import serializers
from django.utils import timezone
from apps.account.models import User
from apps.billing.models import Plan, Subscription, Payment


class PlanSerializer(serializers.ModelSerializer):

    class Meta:
        model = Plan
        fields = ["id", "name"]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan             = PlanSerializer()
    status_display   = serializers.CharField(source="get_status_display", read_only=True)
    next_due_display = serializers.DateField(source="next_due", read_only=True)

    class Meta:
        model = Subscription
        fields = ["plan", "status", "status_display", "next_due", "next_due_display"]


class PaymentSerializer(serializers.ModelSerializer):
    subscription     = SubscriptionSerializer()
    status_display   = serializers.CharField(source="get_status_display", read_only=True)
    paid_at_display  = serializers.DateField(source="paid_at", read_only=True)
    due_date_display = serializers.DateField(source="due_date", read_only=True)

    class Meta:
        model = Payment
        fields = ["subscription", "status", "status_display", "paid_at", "paid_at_display", "due_date", "due_date_display"]


class CreditCardSerializer(serializers.Serializer):
    cpf            = serializers.CharField(max_length=14)
    holder_name    = serializers.CharField(max_length=100)
    number         = serializers.CharField(max_length=19)
    expiry_date    = serializers.CharField(max_length=5)
    ccv            = serializers.CharField(max_length=3)

    def validate_cpf(self, value):
        cpf = re.sub(r"\D", "", value)

        if len(cpf) != 11:
            raise serializers.ValidationError("Número de CPF inválido")

        return cpf

    def validate_number(self, value):
        number = re.sub(r"\D", "", value)

        if len(number) != 16:
            raise serializers.ValidationError("Número do cartão inválido")

        return number

    def validate_expiry_date(self, value):
        try:
            expiry_date = [number for number in value.split("/")]

            if not (1 <= int(expiry_date[0]) <= 12):
                raise serializers.ValidationError("Mês inválido")

            if not (24 <= int(expiry_date[1]) <= 99):
                raise serializers.ValidationError("Ano inválido")
        except (ValueError, IndexError):
            raise serializers.ValidationError("Data em formato incorreto")

        return expiry_date


class SubscriptionSignSerializer(CreditCardSerializer):
    full_name      = serializers.CharField(max_length=100)
    email          = serializers.EmailField(max_length=100)
    password       = serializers.CharField(min_length=8, max_length=32)
    phone_number   = serializers.CharField(max_length=20)
    birth_date     = serializers.DateField()
    postal_code    = serializers.CharField(max_length=10)
    address_number = serializers.CharField(max_length=10)
    plan           = serializers.CharField(max_length=50)
    billing_type   = serializers.ChoiceField(choices=["CREDIT_CARD", "PIX"])

    def validate_plan(self, value):
        try:
            return Plan.objects.get(name__iexact=value, active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError("Esse plano não existe ou está inativo no momento")

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado, acesse a conta e renove sua assinatura")

        return value

    def validate_phone_number(self, value):
        phone_number = re.sub(r"\D", "", value)

        if len(phone_number) != 11:
            raise serializers.ValidationError("Número de telefone inválido")

        return phone_number

    def validate_birth_date(self, value):
        if value.year < 1900:
            raise serializers.ValidationError("O ano de nascimento não pode ser inferior a 1900.")

        today = timezone.now().date()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))

        if age < 18:
            raise serializers.ValidationError("Você deve ter pelo menos 18 anos.")

        return value

    def validate_postal_code(self, value):
        postal_code = re.sub(r"\D", "", value)

        if len(postal_code) != 8:
            raise serializers.ValidationError("Número de CEP inválido")

        return postal_code


class SubscriptionRenewSerializer(CreditCardSerializer):
    plan         = serializers.CharField(max_length=50)
    billing_type = serializers.ChoiceField(choices=["CREDIT_CARD", "PIX"])

    def validate_plan(self, value):
        try:
            return Plan.objects.get(name__iexact=value, active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError("Esse plano não existe ou está inativo no momento")
