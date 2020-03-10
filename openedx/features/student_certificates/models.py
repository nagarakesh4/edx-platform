import re
from random import sample

from django.db import models
from django.urls import reverse

from lms.djangoapps.certificates.models import GeneratedCertificate
from constants import (
    HEX_ROT_10_MAP,
    CERTIFICATE_VERIFICATION_SALT_CHARACTERS,
    CERTIFICATE_VERIFICATION_KEY_LENGTH
)


class CertificateVerificationKeyCreateManager(models.Manager):
    def create_object(self, generated_certificate):
        key = CertificateVerificationKey.generate_hash(generated_certificate)
        return self.create(generated_certificate=generated_certificate, verification_key=key)


class CertificateVerificationKey(models.Model):
    generated_certificate = models.OneToOneField(GeneratedCertificate, related_name='certificate_verification_key',
                                                 on_delete=models.CASCADE)
    verification_key = models.CharField(max_length=32)

    objects = CertificateVerificationKeyCreateManager()

    @staticmethod
    def generate_hash(certificate):
        key_in_hex = format(certificate.pk, 'x').upper()
        rotated_key = ''.join(map(lambda x: HEX_ROT_10_MAP[x], key_in_hex))

        salt_weight = CERTIFICATE_VERIFICATION_KEY_LENGTH - len(rotated_key)

        if salt_weight > 0:
            rotated_key = ''.join(sample(CERTIFICATE_VERIFICATION_SALT_CHARACTERS, salt_weight)) + rotated_key

        return rotated_key

    @property
    def verification_url(self):
        return reverse('certificate_verification', kwargs={'key': self.verification_key})
