from django.db import models
from apps.account.models import User


class Plan(models.Model):

    class Cycle(models.TextChoices):
        WEEKLY       = "WEEKLY",       "Semanal"
        MONTHLY      = "MONTHLY",      "Mensal"
        QUARTERLY    = "QUARTERLY",    "Trimestral"
        SEMIANNUALLY = "SEMIANNUALLY", "Semestral"
        ANNUALLY     = "ANNUALLY",     "Anual"

    name          = models.CharField(max_length=50, verbose_name="Nome")
    value         = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor")
    cycle         = models.CharField(max_length=20, choices=Cycle.choices, verbose_name="Ciclo")
    active        = models.BooleanField(default=False, verbose_name="Ativo")
    free_period   = models.PositiveIntegerField(default=0, verbose_name="Período Gratuito")
    refund_period = models.PositiveIntegerField(default=7, verbose_name="Período de Reembolso")
    created_at    = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "plano"
        verbose_name_plural = "planos"


class Customer(models.Model):
    customer_id = models.CharField(max_length=50, unique=True, verbose_name="Código do Cliente")
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer", verbose_name="Usuário")
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def __str__(self):
        return self.customer_id

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"


class Subscription(models.Model):

    class BillingType(models.TextChoices):
        PIX         = "PIX",         "Pix"
        CREDIT_CARD = "CREDIT_CARD", "Cartão de Crédito"

    class Status(models.TextChoices):
        ACTIVE   = "ACTIVE",   "Ativa"
        INACTIVE = "INACTIVE", "Inativa"

    subscription_id             = models.CharField(max_length=50, unique=True, verbose_name="Código da Assinatura")
    pix_authorization_id        = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Código de Autorização do Pix Automático")
    pix_conciliation_identifier = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Identificador de Conciliação do Pix Automático")
    credit_card_token           = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="Código de Autorização do Cartão de Crédito")
    customer                    = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="subscriptions", verbose_name="Código do Cliente")
    plan                        = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions", verbose_name="Plano")
    billing_type                = models.CharField(max_length=20, choices=BillingType.choices, verbose_name="Tipo de Cobrança")
    status                      = models.CharField(max_length=20, choices=Status.choices, default=Status.INACTIVE, verbose_name="Status")
    next_due                    = models.DateField(null=True, blank=True, verbose_name="Próximo Vencimento")
    created_at                  = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def __str__(self):
        return self.subscription_id

    def clean(self):
        super().clean()
        if self.pix_conciliation_identifier == "":
            self.pix_conciliation_identifier = None
        if self.pix_authorization_id == "":
            self.pix_authorization_id = None
        if self.credit_card_token == "":
            self.credit_card_token = None

    def save(self, *args, **kwargs):
        if self.pix_conciliation_identifier == "":
            self.pix_conciliation_identifier = None
        if self.pix_authorization_id == "":
            self.pix_authorization_id = None
        if self.credit_card_token == "":
            self.credit_card_token = None
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "assinatura"
        verbose_name_plural = "assinaturas"


class SubscriptionHistory(models.Model):

    class Status(models.TextChoices):
        ACTIVE   = "ACTIVE",   "Ativa"
        INACTIVE = "INACTIVE", "Inativa"

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="subscription_histories", verbose_name="Código da Assinatura")
    plan         = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscription_histories", verbose_name="Plano")
    status       = models.CharField(max_length=20, choices=Status.choices, verbose_name="Status")
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def __str__(self):
        return self.subscription.subscription_id

    class Meta:
        verbose_name = "histórico de assinatura"
        verbose_name_plural = "histórico de assinaturas"


class Payment(models.Model):

    class BillingType(models.TextChoices):
        PIX         = "PIX",         "Pix"
        CREDIT_CARD = "CREDIT_CARD", "Cartão de Crédito"

    class Status(models.TextChoices):
        PENDING   = "PENDING",   "Pendente"
        CONFIRMED = "CONFIRMED", "Confirmado"
        RECEIVED  = "RECEIVED",  "Recebido"
        OVERDUE   = "OVERDUE",   "Vencido"
        REFUNDED  = "REFUNDED",  "Reembolsado"

    payment_id   = models.CharField(max_length=50, unique=True, verbose_name="Código da Cobrança")
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.CASCADE, related_name="payments", verbose_name="Código da Assinatura")
    customer     = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="payments", verbose_name="Código do Cliente")
    billing_type = models.CharField(max_length=20, choices=BillingType.choices, verbose_name="Tipo de Cobrança")
    value        = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor")
    status       = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="Status da Cobrança")
    paid_at      = models.DateField(null=True, blank=True, verbose_name="Data de Pagamento")
    due_date     = models.DateField(verbose_name="Data de Vencimento")
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def __str__(self):
        return self.payment_id

    class Meta:
        verbose_name = "cobrança"
        verbose_name_plural = "cobranças"


class Webhook(models.Model):
    webhook_id   = models.CharField(max_length=50, unique=True, verbose_name="Código do Webhook")
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.CASCADE, related_name="webhooks", verbose_name="Código da Assinatura")
    customer     = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE, related_name="webhooks", verbose_name="Código do Cliente")
    event        = models.CharField(max_length=50, db_index=True, verbose_name="Evento")
    payload      = models.JSONField(verbose_name="Payload")
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name="Data de criação")

    def __str__(self):
        return self.webhook_id

    class Meta:
        verbose_name = "webhook"
        verbose_name_plural = "webhooks"
