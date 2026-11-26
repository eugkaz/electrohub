
from django.urls import path
from .views import (
    marketplace_view, listing_detail, create_listing,
    listing_edit, listing_delete, toggle_favorite_listing,
    marketplace_category_view,
    get_or_create_chat, get_chat_messages, upload_chat_image,
    hide_chat_room, delete_chat_message, edit_chat_message
)



urlpatterns = [
    path('', marketplace_view, name="marketplace-view"),
    path('category/<slug:category_slug>/', marketplace_category_view, name='marketplace_category_view'),
    path('listing/create/', create_listing, name='listing_create'),
    path('listing/<int:pk>/', listing_detail, name='listing_detail'),
    path('listing/<int:pk>/edit/', listing_edit, name='listing_edit'),
    path('listing/<int:pk>/delete/', listing_delete, name='listing_delete'),
    path('listing/<int:listing_id>/toggle_favorite/', toggle_favorite_listing, name='toggle_favorite_listing'),

    
    
    path('chat/start/<int:listing_id>/', get_or_create_chat, name='start_chat'),
    
    path('chat/messages/<uuid:room_id>/', get_chat_messages, name='get_chat_messages'),
    path('chat/upload_image/', upload_chat_image, name='chat_upload_image'),
    path('chat/hide/<uuid:room_id>/', hide_chat_room, name='hide_chat_room'),
    path('chat/message/delete/<int:message_id>/', delete_chat_message, name='delete_chat_message'),
    path('chat/message/edit/<int:message_id>/', edit_chat_message, name='edit_chat_message'),
]