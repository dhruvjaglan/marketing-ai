from django.db import models
from django.contrib.auth.models import User


# Create your models here.

class Company(models.Model):
    name = models.CharField(max_length=100)
    legal_name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    detailed_descrption = models.TextField(blank=True, null=True)
    problem_statement = models.JSONField(blank=True, null=True)
    customer_list =  models.JSONField(blank=True, null=True)
    links = models.JSONField(blank=True, null=True)
    details_fetched= models.BooleanField(default=False)
    sector = models.CharField(max_length=100)
    industry = models.CharField(max_length=100, blank=True, null=True)
    domain = models.CharField(max_length=100, unique=True)
    tags = models.JSONField(default=list, blank=True)
    founded_year = models.IntegerField(blank=True, null=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    logo = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    raw_data = models.JSONField(blank=True, null=True)


class CaseStudy(models.Model):
    name = models.TextField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    customer_comment = models.JSONField(blank=True, null=True)
    problem_statement = models.TextField(blank=True, null=True)
    impact = models.TextField(blank=True, null=True)
    customers_name = models.CharField(blank=True, null=True,max_length=100)
    customer_type = models.TextField(blank=True, null=True)
    link = models.URLField(blank=True, null=True, unique=True)
    raw_text  = models.TextField(blank=True, null=True)
    

class Person(models.Model):
    full_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name =  models.CharField(max_length=100, blank=True, null=True)
    title = models.CharField(max_length=100, blank=True, null=True)
    seniority = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True, null=True)
    site = models.URLField(blank=True, null=True)
    avatar = models.URLField(blank=True, null=True)
    linkedin_handle=models.CharField(max_length=100, blank=True, null=True)
    raw_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, null=True, blank=True)
    auth_user = models.ForeignKey(User,
                                    on_delete=models.PROTECT, null=True, blank=True)


### Todo imporve the structure
class CompanyMarketSegment(models.Model):
    name = models.TextField()
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    person = models.ForeignKey(Person, on_delete=models.PROTECT, null=True, blank=True)
    raw_messages = models.JSONField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    conversation_ended = models.BooleanField(default=False)
    conversation = models.JSONField(null=True, blank=True)
    final_search_fields = models.JSONField(null=True, blank=True)
    final_query = models.TextField(null=True, blank=True)
    search_results = models.JSONField(null=True, blank=True)
    raw_response = models.JSONField(null=True, blank=True)
    raw_industries = models.TextField(null=True, blank=True)
    problem = models.TextField(null=True, blank=True)


class EmailSuggestions(models.Model):
    segment = models.ForeignKey(CompanyMarketSegment, on_delete=models.PROTECT)
    case_study_ids = models.TextField()
    subject = models.TextField()
    body = models.TextField()
