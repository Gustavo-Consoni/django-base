from django.views import View
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache


class Home(View):

    def get(self, request):
        return render(request, "pages/home/index.html")


class TermsOfUse(View):

    def get(self, request):
        return render(request, "pages/home/terms_of_use.html")


class PrivacyPolicy(View):

    def get(self, request):
        return render(request, "pages/home/privacy_policy.html")


@method_decorator(never_cache, name="dispatch")
class ServiceWorker(View):

    def get(self, request):
        return render(request, "serviceworker.js", content_type="application/javascript")


@method_decorator(never_cache, name="dispatch")
class Manifest(View):

    def get(self, request):
        return render(request, "manifest.json", content_type="application/manifest+json")


class Offline(View):

    def get(self, request):
        return render(request, "offline.html")
