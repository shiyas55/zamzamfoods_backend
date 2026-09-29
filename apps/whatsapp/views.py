import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from apps.customers.models import Customer
from .models import WhatsAppConversation, WhatsAppMessage, WhatsAppAccount
from .serializers import (
    WhatsAppConversationListSerializer,
    WhatsAppConversationDetailSerializer,
    WhatsAppMessageSerializer,
)
from .services import (
    verify_meta_webhook,
    process_meta_webhook_payload,
    clean_phone_digits,
)

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(APIView):
    """
    Official Meta WhatsApp Cloud API Webhook Endpoint.
    - GET: Handles Meta Webhook Verification Challenge (hub.mode, hub.verify_token, hub.challenge)
    - POST: Receives and processes real-time WhatsApp incoming messages and status events
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        hub_mode = request.GET.get("hub.mode")
        hub_token = request.GET.get("hub.verify_token")
        hub_challenge = request.GET.get("hub.challenge")

        challenge = verify_meta_webhook(hub_mode, hub_token, hub_challenge)
        if challenge:
            return HttpResponse(challenge, content_type="text/plain", status=200)
        return HttpResponse("Verification token mismatch", content_type="text/plain", status=403)

    def post(self, request, *args, **kwargs):
        payload = request.data
        try:
            result = process_meta_webhook_payload(payload)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Error processing WhatsApp Cloud API webhook: %s", str(e), exc_info=True)
            # Always return 200 to Meta to acknowledge receipt so Meta does not disable the webhook
            return Response({"status": "error_handled", "message": str(e)}, status=status.HTTP_200_OK)


class WhatsAppConversationListView(generics.ListAPIView):
    """
    Lists WhatsApp conversations for the authenticated tenant/shop.
    Sorted by latest incoming message timestamp.
    Supports search query (?q=) across shop name, owner, phone, and message body.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WhatsAppConversationListSerializer

    def get_queryset(self):
        user = self.request.user
        shop = getattr(user, "shop", "default") or "default"
        qs = WhatsAppConversation.objects.filter(shop=shop).select_related("customer", "customer__route").order_by("-last_message_at", "-created_at")

        q = self.request.query_params.get("q", "").strip()
        if q:
            digits = clean_phone_digits(q)
            q_filter = (
                Q(customer__name__icontains=q) |
                Q(customer__owner_name__icontains=q) |
                Q(whatsapp_phone__icontains=q) |
                Q(last_message__icontains=q)
            )
            if digits:
                q_filter |= Q(whatsapp_phone__icontains=digits)
            qs = qs.filter(q_filter)

        return qs


class WhatsAppConversationDetailView(generics.RetrieveAPIView):
    """
    Retrieves full details of a single WhatsApp conversation thread including messages.
    Automatically resets unread count when viewed.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WhatsAppConversationDetailSerializer

    def get_queryset(self):
        user = self.request.user
        shop = getattr(user, "shop", "default") or "default"
        return WhatsAppConversation.objects.filter(shop=shop).select_related("customer", "customer__route").prefetch_related("messages")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.unread_count > 0:
            instance.unread_count = 0
            instance.save(update_fields=["unread_count", "updated_at"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class WhatsAppConversationMessagesView(generics.ListAPIView):
    """
    Retrieves the chronological message history for a given conversation.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WhatsAppMessageSerializer

    def get_queryset(self):
        user = self.request.user
        shop = getattr(user, "shop", "default") or "default"
        conversation_id = self.kwargs.get("pk")
        return WhatsAppMessage.objects.filter(
            conversation__id=conversation_id,
            conversation__shop=shop
        ).order_by("timestamp")


class WhatsAppCustomerConversationView(APIView):
    """
    Retrieves or establishes a WhatsApp conversation thread for a specific Zamzam customer ID.
    Used for 2-way seamless customer/shop search -> WhatsApp chat navigation.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id, *args, **kwargs):
        user = request.user
        shop = getattr(user, "shop", "default") or "default"

        customer = Customer.objects.filter(id=customer_id).first()
        if not customer:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        # 1. Look for existing conversation linked to this customer
        conversation = WhatsAppConversation.objects.filter(shop=shop, customer=customer).first()

        # 2. Look for conversation linked to customer's phone digits
        if not conversation and customer.phone:
            digits = clean_phone_digits(customer.phone)
            if digits:
                conversation = WhatsAppConversation.objects.filter(
                    shop=shop,
                    whatsapp_phone__endswith=digits[-10:] if len(digits) >= 10 else digits
                ).first()
                if conversation and not conversation.customer:
                    conversation.customer = customer
                    conversation.save(update_fields=["customer", "updated_at"])

        # 3. If no conversation exists yet, create an empty pending thread for this customer
        if not conversation:
            digits = clean_phone_digits(customer.phone) or "0000000000"
            conversation = WhatsAppConversation.objects.create(
                shop=shop,
                customer=customer,
                whatsapp_phone=digits,
                last_message="[No incoming messages yet]",
                unread_count=0
            )

        if conversation.unread_count > 0:
            conversation.unread_count = 0
            conversation.save(update_fields=["unread_count", "updated_at"])

        serializer = WhatsAppConversationDetailSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_200_OK)
