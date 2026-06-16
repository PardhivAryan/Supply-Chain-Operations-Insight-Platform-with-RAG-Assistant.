from django.urls import path

from . import views


app_name = "analytics"

urlpatterns = [
    path("health/", views.health, name="health"),
    path("", views.home, name="home"),
    path("login/", views.LocalLoginView.as_view(), name="login"),
    path("logout/", views.LocalLogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("upload/", views.upload, name="upload"),
    path("orders/", views.orders, name="orders"),
    path("chatbot/", views.chatbot, name="chatbot"),
    path("chatbot/clear-history/", views.clear_chat_history, name="clear_chat_history"),
    path("reports/", views.reports, name="reports"),
    path("api/kpis/", views.api_kpis, name="api_kpis"),
    path("api/charts/monthly-revenue/", views.api_monthly_revenue, name="api_monthly_revenue"),
    path("api/charts/category-revenue/", views.api_category_revenue, name="api_category_revenue"),
    path("api/charts/region-late-delivery/", views.api_region_late_delivery, name="api_region_late_delivery"),
    path("api/charts/shipping-mode/", views.api_shipping_mode, name="api_shipping_mode"),
    path("api/charts/country-revenue/", views.api_country_revenue, name="api_country_revenue"),
    path("api/chat/", views.api_chat, name="api_chat"),
]
