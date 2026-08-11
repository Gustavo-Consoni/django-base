from django.views import View
from django.shortcuts import render


class SubscriptionCheckout(View):

    def get(self, request):
        return render(request, "pages/billing/subscription_checkout.html")


class SubscriptionCompleted(View):

    def get(self, request):
        return render(request, "pages/billing/subscription_completed.html")
