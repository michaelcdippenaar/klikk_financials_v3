from django.db import models


class XeroTenant(models.Model):
    tenant_id = models.CharField(max_length=100, unique=True, primary_key=True)
    tenant_name = models.CharField(max_length=100)

    def __str__(self):
        return self.tenant_name
