from unfold.admin import ModelAdmin
from django.contrib import admin
from apps.notification import models
from apps.notification.tasks import notify_user


@admin.register(models.WebpushSubscription)
class WebpushSubscriptionAdmin(ModelAdmin):
    list_per_page = 20
    list_display = ["user", "updated_at"]
    actions = ["send_test_notification_action"]

    def send_test_notification_action(self, request, queryset):
        for subscription in queryset:
            notify_user.delay(
                user_id=subscription.user_id,
                title="Notificação de Teste",
                body="Esta é uma notificação de teste enviada pelo Django Admin",
            )
        self.message_user(request, "Notificação de teste enviada para as subscriptions selecionadas.")
    send_test_notification_action.short_description = "Enviar notificação de teste para selecionados"
