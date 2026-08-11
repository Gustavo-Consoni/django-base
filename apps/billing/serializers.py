import re
from rest_framework import serializers
from apps.account.models import User
from apps.billing.models import Plan


class SubscriptionSignSerializer(serializers.Serializer):
    plan           = serializers.IntegerField(required=False, default=1)
    full_name      = serializers.CharField(max_length=100)
    email          = serializers.EmailField(max_length=100)
    password       = serializers.CharField(min_length=8, max_length=32)
    cnpj           = serializers.CharField(max_length=18)
    phone_number   = serializers.CharField(max_length=15)
    postal_code    = serializers.CharField(max_length=9)
    address_number = serializers.CharField(max_length=5, required=False, allow_blank=True)
    complement     = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_plan(self, value):
        try:
            return Plan.objects.get(id=value, active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError("Esse plano não existe ou está inativo no momento")

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado, faça login para acessar sua conta")

        return value

    def validate_cnpj(self, value):
        cnpj = re.sub(r"\D", "", value)

        if len(cnpj) != 14:
            raise serializers.ValidationError("Número de CNPJ inválido")

        return cnpj

    def validate_phone_number(self, value):
        phone_number = re.sub(r"\D", "", value)

        if len(phone_number) != 11:
            raise serializers.ValidationError("Número de telefone inválido")

        return phone_number

    def validate_postal_code(self, value):
        postal_code = re.sub(r"\D", "", value)

        if len(postal_code) != 8:
            raise serializers.ValidationError("Número de CEP inválido")

        return postal_code
