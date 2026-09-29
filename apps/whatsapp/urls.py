from django.urls import path
from .views import (
    WhatsAppWebhookView,
    WhatsAppConversationListView,
    WhatsAppConversationDetailView,
    WhatsAppConversationMessagesView,
    WhatsAppCustomerConversationView,
)

app_name = "whatsapp"

urlpatterns = [
    # Meta WhatsApp Webhook (GET for verification, POST for incoming messages)
    path("webhook/", WhatsAppWebhookView.as_view(), name="webhook"),

    # Conversations list (filtered by shop/tenant, search support)
    path("conversations/", WhatsAppConversationListView.as_view(), name="conversation_list"),

    # Single conversation detail (with auto-clear unread)
    path("conversations/<uuid:pk>/", WhatsAppConversationDetailView.as_view(), name="conversation_detail"),

    # Message history for a conversation
    path("conversations/<uuid:pk>/messages/", WhatsAppConversationMessagesView.as_view(), name="conversation_messages"),

    # Resolve or create conversation for a specific customer ID (for 2-way search integration)
    path("customer/<uuid:customer_id>/", WhatsAppCustomerConversationView.as_view(), name="customer_conversation"),
]
