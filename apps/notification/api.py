from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from apps.notification.models import WebpushSubscription


class WebpushSubscribe(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        WebpushSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                "endpoint": request.data["endpoint"],
                "auth": request.data["keys"]["auth"],
                "p256dh": request.data["keys"]["p256dh"],
            },
        )
        return Response(status=status.HTTP_200_OK)


class WebpushResubscribe(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        WebpushSubscription.objects.filter(
            endpoint=request.data["old_endpoint"]
        ).update(
            endpoint=request.data["new_subscription"]["endpoint"],
            auth=request.data["new_subscription"]["keys"]["auth"],
            p256dh=request.data["new_subscription"]["keys"]["p256dh"],
        )
        return Response(status=status.HTTP_200_OK)


class WebpushUnsubscribe(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        WebpushSubscription.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_200_OK)
