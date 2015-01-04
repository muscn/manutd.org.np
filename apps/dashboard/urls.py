from django.conf.urls import patterns, url
from . import views
from apps.payment import views as payment_views


urlpatterns = patterns('',
                       url(r'^$', views.index, name='dashboard_index'),
                       url(r'^payment/$', payment_views.PaymentListView.as_view(), name='list_payments'),
)
