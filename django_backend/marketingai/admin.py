from django.contrib import admin
from .models import Company, Person, CompanyMarketSegment, CaseStudy, EmailSuggestions

# Register your models here.

admin.site.register(Company)
admin.site.register(Person)
admin.site.register(CompanyMarketSegment)
admin.site.register(CaseStudy)
admin.site.register(EmailSuggestions)

