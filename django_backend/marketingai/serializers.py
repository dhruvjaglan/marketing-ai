from rest_framework import serializers, status
from .models import Company, CompanyMarketSegment, EmailSuggestions, Person, CaseStudy, EmailSequence, EmailMailPersonalisation


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

class EmailSequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSequence
        fields = "__all__"

class EmailMailPersonalisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailMailPersonalisation
        fields = [
            'id',
            'person_linkedin_url',
            'company_domain',
            'post_found',
            'sequence_completed',
            'company_name',
            'full_name',
            'title',
            'personalised_email_copy'
        ]

class CaseStudySerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseStudy
        fields = "__all__"

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id',
            'name',
            'description',
            'detailed_descrption',
            'sector',
            'industry',
            'domain',
            'founded_year',
            'logo'
        ]

class PersonSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)

    class Meta:
        model = Person
        fields = [
            'id',
            'full_name',
            'first_name',
            'last_name',
            'title',
            'seniority',
            'email',
            'bio',
            'site',
            'avatar',
            'linkedin_handle',
            'company'
        ]
        depth = 1



class CompanyMarketSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyMarketSegment
        fields = "__all__"


class EmailSuggestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSuggestions
        fields = "__all__"