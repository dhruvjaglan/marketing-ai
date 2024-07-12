from rest_framework import serializers, status
from .models import Company, CompanyMarketSegment, EmailSuggestions, Person


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()



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