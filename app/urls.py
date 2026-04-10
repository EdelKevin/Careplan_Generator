from django.urls import path
from . import views

# urls.py 的意义：门牌号。Django 收到请求后，对照这张表找到对应的函数。
# 就像餐厅门口的指示牌："点餐 → 1号窗口，取餐 → 2号窗口"

urlpatterns = [
    path("", views.home),
    path("api/orders/", views.create_order),
    path("api/careplans/<int:job_id>/", views.get_careplan),
    path("api/careplans/<int:job_id>/status/", views.careplan_status),
    path("api/careplans/<int:job_id>/download/", views.download_careplan),
]
