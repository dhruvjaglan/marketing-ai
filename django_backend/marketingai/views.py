from django.shortcuts import render
from rest_framework.decorators import api_view
import json
from rest_framework import generics
from rest_framework.response import Response
from marketingai.constants import MARGET_SEGMENT_CONVERSATION
from marketingai.filters_utils import get_formatted_query
from marketingai.tasks import add_company_details
from marketingai.models import CompanyMarketSegment, Person, Company, EmailSuggestions, CaseStudy
from marketingai.utils import fill_template, get_company_person_info, get_conversation_next_turn, get_email_messages, get_emails, get_industry_problems, get_people_search_results, get_search_filters, get_search_results
from marketingai.serializers import CompanyMarketSegmentSerializer, EmailSuggestionsSerializer, EmailSerializer, PersonSerializer, CaseStudySerializer

# Create your views here.
@api_view(['POST'])
def create_company_user(request):
    data= request.data
    serializer = EmailSerializer(data=data)
    if (serializer.is_valid()):
        email= serializer.validated_data.get("email")
        person=Person.objects.filter(email=email)
        if person.exists():
            person=person[0]
        else:
            person = get_company_person_info(email)
        
        if (person.company and person.company.domain and not person.company.details_fetched):
                url = "https://" + person.company.domain
                add_company_details.delay(url, person.company.id)

        return Response(PersonSerializer(person).data)

    return Response(status=400, data=serializer.errors)

@api_view(['GET'])
def get_case_study(request, pk):
    company = Company.objects.get(pk=pk)
    case_study = CaseStudy.objects.filter(company=company)
    return Response(CaseStudySerializer(case_study, many=True).data)


@api_view(['GET'])
def get_detailed_description(request, pk):
    company = Company.objects.get(pk=pk)

    if not company.details_fetched:
        return Response(status=400)

    return Response(status=200, data={
            "description": company.description,
            "problem_statement": company.problem_statement,
            "customer_list": company.customer_list
        })

## TODO add functionality to update details

@api_view(['POST'])
def update_description(request):
    data= request.data
    company_id = data.get("company_id")
    description = data.get("description")
    company = Company.objects.get(id=company_id)
    company.detailed_descrption=description
    company.save()
    person = Person.objects.get(id=data.get("id"))
    return Response(PersonSerializer(person).data)


### start a new margeting segment
@api_view(['POST'])
def create_new_marketing_segment(request):
    data= request.data
    company_id = data.get("company_id")
    company = Company.objects.get(id=company_id)
    marget_segment = CompanyMarketSegment.objects.create(company=company)
    marget_segment.conversation = fill_template(company.name, company.detailed_descrption, MARGET_SEGMENT_CONVERSATION)
    marget_segment.raw_messages = [{
        "type": "bot",
        "message": "Tell me who are you plaining to reach out to?"
    }
    ]
    marget_segment.save()

    return Response(status=200, data={
        "id": marget_segment.id
    })

@api_view(['POST'])
def get_final_filters(request, pk):
    marget_segment = CompanyMarketSegment.objects.get(id=pk)
    data= request.data
    message = data.get("message")
    marget_segment.message=message
    raw_filters = get_search_filters(message)


    if raw_filters:
        if raw_filters.get("name"):
            marget_segment.name= raw_filters.get("name")
        filters, query = get_formatted_query(raw_filters) ### get search filter too
        marget_segment.final_search_fields=filters
        marget_segment.final_query = query
        marget_segment.save()

        return Response(status=200, data={
            "search_filters": filters
        })
    else:
        return Response(status=400)
        


@api_view(['POST'])
def send_message(request, pk):
    marget_segment = CompanyMarketSegment.objects.get(id=pk)
    data= request.data
    raw_messages = marget_segment.raw_messages
    message = data.get("message")

    raw_messages.append(
        {
            "type": "user",
            "message": message
        }
    )
    
    conversation = marget_segment.conversation
    conversation.append(
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": message
                }
            ]
            }
            )
    
    next_message  = get_conversation_next_turn(conversation)
    next_message_parsed = json.loads(next_message)

    if next_message_parsed.get("name"):
        marget_segment.name=next_message_parsed.get("name")

    end = next_message_parsed.get("end", False)
    conversation.append({
            "role": "assistant",
            "content": [
                {
                "type": "text",
                "text": next_message
                }
            ]
            }
            )
    raw_messages.append(
        {
            "type": "bot",
            "message": next_message_parsed.get("question")
        }
    )
    marget_segment.raw_messages = raw_messages
    marget_segment.conversation=conversation
    marget_segment.save()

    if end or not next_message_parsed.get("question"):
            # industries = fix_industries(next_message_parsed.get("industry", []))
            # final_search_fields = {
            #     "industries": industries,
            #     "employee_count": next_message_parsed.get("company_size", None),
            #     "country": next_message_parsed.get("country", None),
            #     "job_title": next_message_parsed.get("job_title", None),
            #     }
            # marget_segment.raw_industries=next_message_parsed.get("industry", [])
            marget_segment.conversation_ended = True
            # marget_segment.final_search_fields = final_search_fields
            marget_segment.save()
            return Response(status=200, data={
            "id": marget_segment.id,
            "end": True,
            "message": "Please press search to look for message."
        })

    if not end:
        return Response(status=200, data={
            "id": marget_segment.id,
            "end": False,
            "message": next_message_parsed.get("question")
        }) 

@api_view(['POST'])
def search(request, pk):
    marget_segment = CompanyMarketSegment.objects.get(id=pk)
    ### TODO fetch only when search result changed
    if marget_segment.final_query:
        response = get_search_results(marget_segment.final_query)
        marget_segment.raw_response = response
        marget_segment.search_results = response.get('data')
        marget_segment.save()
        return Response(status=200, data={
            "id": marget_segment.id,
            "profiles": response.get('data'),
            "count": response.get('total')
        })
    else:
        return Response(status=400, data={
            "message": "Something went wrong"
        })


@api_view(['POST'])
def get_mails(request, pk):
    marget_segment = CompanyMarketSegment.objects.get(id=pk)
    data = request.data
    case_study_ids = data.get("case_study_ids", [])
    sorted_array = sorted(case_study_ids)
    comma_separated_string = ','.join(map(str, sorted_array))


    emails = EmailSuggestions.objects.filter(segment=marget_segment, case_study_ids=comma_separated_string)

    if not emails.exists():
        raw_emails = get_emails(marget_segment.company.id, case_study_ids, marget_segment.id)

        for mail in raw_emails:
            EmailSuggestions.objects.create(segment=marget_segment, subject=mail.get("subject"), body=mail.get("body"), case_study_ids=comma_separated_string)
        
        emails = EmailSuggestions.objects.filter(segment=marget_segment, case_study_ids=comma_separated_string)
    
    return Response(status=200, data=EmailSuggestionsSerializer(emails, many=True).data)


def create_user_view(request):
    # Render the create_user.html template
    return render(request, 'create_user.html')


def create_home_view(request):
    # Render the create_user.html template
    return render(request, 'home.html')



class CompanyMarketSegmentListAPIView(generics.ListAPIView):
    serializer_class = CompanyMarketSegmentSerializer

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return CompanyMarketSegment.objects.filter(company_id=company_id)



def segment_view(request, segment_id):
    # Assuming Chat model has a ForeignKey to Segment model
    # chats = Chat.objects.filter(segment_id=segment_id).order_by('-timestamp')  # Fetch chats ordered by timestamp (newest first)
    segment = CompanyMarketSegment.objects.get(id=segment_id)  # Assuming Segment model exists

    filters= None

    if segment.final_search_fields:
        filters = {k: v for k, v in segment.final_search_fields.items() if v  and k != "name"}


    context = {
        'name': segment.name,
        'id': segment.id,
        'end': segment.conversation_ended,
        'message': segment.message,
        'company_id': segment.company.id,
        'search_filters': filters,
        "profiles" : segment.search_results,
        "count": segment.raw_response.get('total', None) if segment.raw_response else None
    }
    return render(request, 'search_view.html', context)


def search_results_view(request, segment_id):
    marget_segment = CompanyMarketSegment.objects.get(id=segment_id)
    if marget_segment.final_search_fields and not marget_segment.search_results:
        response = get_people_search_results(marget_segment.final_search_fields)
        marget_segment.raw_response = response
        marget_segment.search_results = response.get('data')
        marget_segment.save()
        
    context = {
        "id": marget_segment.id,
        "profiles": marget_segment.search_results,
        "count": marget_segment.raw_response.get('total')
    }

    return render(request, 'search_result.html', context)

