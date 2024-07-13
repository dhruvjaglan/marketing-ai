from django.shortcuts import render
from rest_framework.decorators import api_view
import json
from rest_framework import generics
from rest_framework.response import Response
from marketingai.constants import MARGET_SEGMENT_CONVERSATION
from marketingai.models import CompanyMarketSegment, Person, Company, EmailSuggestions
from marketingai.utils import fill_template, get_company_details, get_company_person_info, get_conversation_next_turn, fix_industries, get_email_messages, get_industry_problems, get_people_search_results
from marketingai.serializers import CompanyMarketSegmentSerializer, EmailSuggestionsSerializer, EmailSerializer, PersonSerializer

# Create your views here.
@api_view(['POST'])
def create_company_user(request):
    data= request.data
    serializer = EmailSerializer(data=data)
    if (serializer.is_valid()):
        email= serializer.validated_data.get("email")
        person=Person.objects.filter(email=email)
        if person.exists():
            return Response(PersonSerializer(person[0]).data)
        else:
            person = get_company_person_info(email)
            return Response(PersonSerializer(person).data)

    return Response(status=400, data=serializer.errors)

@api_view(['GET'])
def get_detailed_description(request, pk):
    company = Company.objects.get(pk=pk)

    if not company.detailed_descrption:
        details = get_company_details(company.domain)
        company.detailed_descrption = details
        company.save()

    return Response(status=200, data={
            "description": company.detailed_descrption
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

    if end:
            industries = fix_industries(next_message_parsed.get("industry", []))
            final_search_fields = {
                "industries": industries,
                "employee_count": next_message_parsed.get("company_size", None),
                "country": next_message_parsed.get("country", None),
                "job_title": next_message_parsed.get("job_title", None),
                }
            marget_segment.raw_industries=next_message_parsed.get("industry", [])
            marget_segment.conversation_ended = True
            marget_segment.final_search_fields = final_search_fields
            marget_segment.save()
            return Response(status=200, data={
            "id": marget_segment.id,
            "end": True,
            "message": "Thanks, here are your search filters.",
            "search_filters": final_search_fields
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
    if marget_segment.final_search_fields and not marget_segment.search_results:
        response = get_people_search_results(marget_segment.final_search_fields)
        marget_segment.raw_response = response
        marget_segment.search_results = response.get('data')
        marget_segment.save()
        return Response(status=200, data={
            "id": marget_segment.id,
            "profiles": response.get('data'),
            "count": response.get('total')
        })
    elif marget_segment.search_results:
        return Response(status=200, data={
            "id": marget_segment.id,
            "profiles": marget_segment.search_results,
            "count": marget_segment.raw_response.get('total')
        })
    else:
        return Response(status=400, data={
            "message": "Something went wrong"
        })


@api_view(['GET'])
def get_mails(request, pk):
    marget_segment = CompanyMarketSegment.objects.get(id=pk)

    if not marget_segment.problem:
        problem = get_industry_problems(marget_segment.raw_industries, marget_segment.company.name, marget_segment.company.detailed_descrption)
        marget_segment.problem = problem
        marget_segment.save()

    
    emails = EmailSuggestions.objects.filter(segment=marget_segment)

    if not emails.exists():
        raw_emails = get_email_messages(marget_segment.company.name, marget_segment.problem, marget_segment.company.detailed_descrption)

        for mail in raw_emails:
            EmailSuggestions.objects.create(segment=marget_segment, subject=mail.get("subject"), body=mail.get("body"))
        
        emails = EmailSuggestions.objects.filter(segment=marget_segment)
    
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

    context = {
        'name': segment.name,
        'id': segment.id,
        'end': segment.conversation_ended,
        'chats': segment.raw_messages,
        'search_filters': segment.final_search_fields,
    }
    return render(request, 'segment_chat.html', context)


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
    print(context)

    return render(request, 'search_result.html', context)

