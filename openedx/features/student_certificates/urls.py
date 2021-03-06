"""
The urls for philu features app.
"""
from django.conf.urls import url

from openedx.features.student_certificates import views

urlpatterns = [
    url(r"^certificates/$", views.student_certificates, name="certificates"),
    url(r"^achievements/(?P<certificate_uuid>[0-9a-f]{32})$", views.shared_student_achievements,
        name="shared_achievements"),
    url(r'^certificates/(?P<certificate_uuid>[0-9a-f]{32})/download$', views.download_certificate_pdf,
        name='download_certificate_pdf'),
    url(r"^verify/(?P<key>[A-Z]{10,16})$", views.verify_certificate, name="certificate_verification"),
]
