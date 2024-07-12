from django.contrib import admin
from .models import Company, Person, CompanyMarketSegment

# Register your models here.

admin.site.register(Company)
admin.site.register(Person)
admin.site.register(CompanyMarketSegment)
