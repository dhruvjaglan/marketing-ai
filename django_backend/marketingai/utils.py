import requests
from django.conf import settings
import json
from marketingai.constants import EMAIL_TEMPLATE, INDUSTRIES_FIX_PROMPT, INDUSTRY_PROBLEMS
from .models import Person, Company
from openai import OpenAI
from peopledatalabs import PDLPY
import logging

logger = logging.getLogger(__name__)


client = OpenAI(
    # This is the default and can be omitted
    api_key=settings.OPENAI_AI_KEY,
)

def get_company_person_info(email):
    url="https://person-stream.clearbit.com/v2/combined/find?email="+email

    payload={}
    auth_token='Bearer ' + settings.CLEARBIT_API_KEY
    headers={
    'Authorization': auth_token
    }

    response=requests.request("GET", url, headers=headers, data=payload)

    company=None
    person=None
    
    if response.json()['company']:
        data=response.json()['company']
        try:
            companies = Company.objects.filter(domain=data['domain'])
            if companies.exists():
                company = companies[0]
            else:
                company=Company(
                        name=data.get('name', 'NA'),
                        legal_name=data.get('legalName', 'NA'),
                        description=data.get('description', 'NA'),
                        raw_data=data,
                        sector=data.get('category', {}).get("sector"),
                        industry=data.get('category', {}).get("industry"),
                        domain=data['domain'],
                        tags=data['tags'],
                        founded_year=data['foundedYear'],
                        timezone=data['timeZone'],
                        logo=data['logo']
                    )
                company.save()
        except Exception as e:
            logger.error(e)


    if response.json()['person']:
        data=response.json()['person']
        person=Person(
            full_name=data.get('name', {}).get("fullName", 'NA'),
            first_name=data.get('name', {}).get("givenName", 'NA'),
            last_name=data.get('name', {}).get("familyName", 'NA'),
            title=data.get('employment', {}).get("title", 'NA'),
            seniority=data.get('employment', {}).get("seniority", 'NA'),
            email=email,
            bio=data.get('bio'),
            site=data.get('site', None),
            avatar=data.get('avatar', None),
            linkedin_handle=data.get('linkedin', {}).get('handle', None),
            raw_data=data,
            company=company
        )

        person.save()
    else:
        person=Person(email=email,company=company,raw_data=response.json())
        person.save()


    return person
    

def get_company_details(domain):
    messages = [
    {
        "role": "system",
        "content": (
            "You are an artificial intelligence assistant and you need to "
            "engage in a helpful, detailed, polite conversation with a user."
        ),
    },
    {
        "role": "user",
        "content": (
            "go through "+ domain +" website, and describe what does the company do and offer"
        ),
    },
]

    client = OpenAI(api_key=settings.PERPLEXITY_API_KEY, base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = client.chat.completions.create(
        model="llama-3-sonar-large-32k-online",
        messages=messages,
    )
    return response.choices[0].message.content


                # "industries": industries,
                # "employee_count": next_message_parsed.get("company_size", None),
                # "country": next_message_parsed.get("country", None),
                # "job_title": next_message_parsed.get("job_title", None),
                # }

def get_search_results(query):
    client = PDLPY(
        api_key=settings.PEOPLE_DATA_LABS_API_KEY,
    )
    PARAMS = {
        'dataset': 'email',
        'sql': query,
        'size': 3,
        'pretty': True
    }
    
    response = client.person.search(**PARAMS).json()

    return response


def get_people_search_results(search_fields):
    client = PDLPY(
        api_key=settings.PEOPLE_DATA_LABS_API_KEY,
    )
    sql_query = "SELECT * FROM person WHERE"
    count = 0

    if search_fields.get("industries", None):
        industries = ', '.join("'" + industry.lower() + "'" for industry in search_fields.get("industries"))
        count+=1
        sql_query += " job_company_industry IN ("+ industries + ")"
    if search_fields.get("employee_count", None):
        count+=1
        if count> 0:
            sql_query += " And"
        sql_query+=" job_company_employee_count >= " + str(search_fields.get("employee_count"))
    if search_fields.get("country", None):
        count+=1
        countries = ', '.join("'" + country.lower() + "'" for country in search_fields.get("country"))
        if count> 0:
            sql_query += " And"
        sql_query+=" job_company_location_country IN ("+ countries + ") AND location_country IN ("+ countries + ")"
    if search_fields.get("job_title", None):
        count+=1
        job_titles = ', '.join("'" + title.lower() + "'" for title in search_fields.get("job_title"))
        if count> 0:
            sql_query += " And"
        sql_query += " job_title IN ("+ job_titles + ")"
    sql_query+= ";"


    PARAMS = {
        'dataset': 'email',
        'sql': sql_query,
        'size': 3,
        'pretty': True
    }
    
    response = client.person.search(**PARAMS).json()

    return response


def fill_template(company_name, company_detail, template):
    filled_template = []
    for entry in template:
        filled_entry = entry.copy()
        filled_entry['content'] = [
            {
                "type": item["type"],
                "text": item["text"].replace("{company_name}", company_name).replace("{company_detail}", company_detail)
            } if isinstance(item, dict) and 'text' in item else item
            for item in entry['content']
        ]
        filled_template.append(filled_entry)
    return filled_template


def fill_template_general(variables, template):
    filled_template = []
    for entry in template:
        filled_entry = entry.copy()
        filled_entry['content'] = []
        for item in entry['content']:
            if isinstance(item, dict) and 'text' in item:
                filled_text = item['text']
                for placeholder, value in variables.items():
                    filled_text = filled_text.replace(f"{{{placeholder}}}", value)
                filled_entry['content'].append({
                    "type": item["type"],
                    "text": filled_text
                })
            else:
                filled_entry['content'].append(item)
        filled_template.append(filled_entry)
    return filled_template


def get_conversation_next_turn(conversation):


    response = client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    return response.choices[0].message.content


def get_industry_problems(industries, company, company_detail):
    prompt = INDUSTRY_PROBLEMS
    prompt = fill_template_general({
        "industry":  industries,
        "company" : company,
        "company_detail": company_detail
    }, prompt)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=prompt,
        temperature=1,
        max_tokens=400,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].message.content

def get_email_messages(company, problem, company_detail):
    prompt = EMAIL_TEMPLATE
    prompt = fill_template_general({
        "target_problem":  problem,
        "company" : company,
        "company_detail": company_detail
    }, prompt)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=prompt,
        temperature=1,
        max_tokens=2000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    return eval(strip_outside_single_pair_brackets(response.choices[0].message.content))

def strip_outside_single_pair_brackets(text):
    start_index = text.find('[')
    end_index = text.find(']')
    
    if start_index != -1 and end_index != -1 and start_index < end_index:
        stripped_text = text[start_index:end_index+1]
        return stripped_text
    
    return None

def get_search_filters(message):
    response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                "role": "system",
                "content": [
                    {
                    "type": "text",
                    "text": "You have to provide people search filters based on what person has said in JSON format.\n\n{\n\"name\": ## give a short readable name for the user search,\n\"location\": [] ### array of locations (try to provide full name of the location instead of short forms,\n\"include_companies\": [] ## companies to include,\n\"exclude_companies\": [] ## companies to exclude,\n\"similar_companies\" : [] ### similar companies,\n\"past_companies\" : [] ### past companies,\n\"job_title\": [] ## array of job titles of the person,\n\"job_title_level: ### array of title level of the person from the following list { cxo, director, entry, manager, owner, partner, senior, training, unpaid, vp},\n\"job_roles\": ## department they are working from this list {advisory, analyst, creative, education, engineering, finance, fulfillment, health, hospitality, human_resources, legal, manufacturing, marketing, operations, partnerships, product, professional_service, public_service,research, sales, sales_engineering, support, trade},\n\"company_size\":  ## Array of type i.e emerging (<50), small (50-200), mid (201-1000), large (1001-5000), enterprise (5000+),\n\"company_funding_stage\": ## array of type (pre-seed, seed, series-a, series-b, series-c, series-d+),\n\"industry\" : ### array of industries,\n\"college\": ### college they graduated from,\n\"field_of_study\": ## field of study during college\n}\n\nAdd everything as null which is not mentioned, Just return Json "
                    }
                ]
                },
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": message
                }
            ]
            }
        ],
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
        )
    

    if response.choices and len(response.choices)> 0:
        model_output = response.choices[0].message.content
        start_index = model_output.find('{')
        end_index = model_output.rfind('}') + 1
        if start_index != -1 and end_index != -1 and start_index < end_index:
            json_string = model_output[start_index:end_index]
            parsed_json = json.loads(json_string)
            return parsed_json
    
    return None


def fix_industries(industries):

    prompt = INDUSTRIES_FIX_PROMPT

    prompt.append({
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": " ,".join(industries)
        }
      ]
    })

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=prompt,
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return eval(response.choices[0].message.content)