from django.urls import path
from .views import IndexView, SendMessageView

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("send-message/", SendMessageView.as_view(), name="send_message"),
]
