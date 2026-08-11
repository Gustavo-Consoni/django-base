from unfold.admin import ModelAdmin
from django.contrib import admin
from apps.billing import models


@admin.register(models.Plan)
class PlanAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ["name", "value", "cycle", "active", "free_period", "refund_period", "created_at"]
    list_filter = ["cycle", "active"]
    search_fields = ["name"]


@admin.register(models.Customer)
class CustomerAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ["user", "created_at"]
    search_fields = ["user__email", "customer_id"]
    autocomplete_fields = ["user"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user")


@admin.register(models.Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ["get_user", "plan", "billing_type", "status", "next_due", "created_at"]
    list_filter = ["plan", "billing_type", "status"]
    search_fields = ["customer__user__email", "customer__customer_id", "subscription_id"]
    autocomplete_fields = ["customer", "plan"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("customer__user", "plan")

    def get_user(self, obj):
        return obj.customer.user.email

    get_user.short_description = "Usuário"
    get_user.admin_order_field = "customer__user__email"


@admin.register(models.SubscriptionHistory)
class SubscriptionHistoryAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ["get_user", "plan", "status", "created_at"]
    list_filter = ["plan", "status"]
    search_fields = ["subscription__customer__user__email", "subscription__customer__customer_id", "subscription__subscription_id"]
    autocomplete_fields = ["subscription", "plan"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("subscription__customer__user", "plan")

    def get_user(self, obj):
        return obj.subscription.customer.user.email

    get_user.short_description = "Usuário"
    get_user.admin_order_field = "subscription__customer__user__email"


@admin.register(models.Payment)
class PaymentAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ["get_user", "value", "billing_type", "status", "paid_at", "due_date", "created_at"]
    list_filter = ["billing_type", "status"]
    search_fields = ["subscription__customer__user__email", "subscription__customer__customer_id", "subscription__subscription_id", "payment_id"]
    autocomplete_fields = ["subscription", "customer"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("subscription__customer__user")

    def get_user(self, obj):
        return obj.subscription.customer.user.email

    get_user.short_description = "Usuário"
    get_user.admin_order_field = "subscription__customer__user__email"


@admin.register(models.Webhook)
class WebhookAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ["get_user", "event", "created_at"]
    list_filter = ["event"]
    search_fields = ["subscription__customer__user__email", "subscription__customer__customer_id", "subscription__subscription_id", "webhook_id"]
    autocomplete_fields = ["subscription", "customer"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("subscription__customer__user")

    def get_user(self, obj):
        return obj.subscription.customer.user.email

    get_user.short_description = "Usuário"
    get_user.admin_order_field = "subscription__customer__user__email"
