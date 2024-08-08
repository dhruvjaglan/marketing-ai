from celery import shared_task
from openai import OpenAI
from django.conf import settings
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from marketingai.utils import get_personalised_mail, get_post_relatability, get_relatable_content
from marketingai.models import CaseStudy, Company, EmailMailPersonalisation
from peopledatalabs import PDLPY
import logging

logger = logging.getLogger(__name__)

client = OpenAI(
    api_key=settings.OPENAI_AI_KEY,
)

@shared_task
def add_company_details(company_link, company_id):
    company = Company.objects.get(id=company_id)
    links = get_all_links(company_link, company.domain, 3)
    formatted_links = format_links(str(links))
    company.links = formatted_links
    if formatted_links and formatted_links.get("customer_case_study"):
        for link in formatted_links.get("customer_case_study"):
            get_case_study(link, company)
    
    company_details = get_company_details(company_link)
    if company_details:
        format_company_details(company_details, company)
    company.details_fetched = True
    company.save()

def format_company_details(company_details, company):
    for i in range(2):
        try:
            response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                "role": "system",
                "content": [
                    {
                    "type": "text",
                    "text": "Format the following details about the company from details provided and return json structure\n\n{\n\"summary\": ### companies quick description,\n\"problem_statement\": #### array of problem statement/customer challenges,\n\"customer_list\": ### array of customer names\n}"
                    }
                ]
                },
                {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": company_details
                    }
                ]
                }
            ],
            temperature=1,
            max_tokens=1169,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )
            if len(response.choices)>0 and response.choices[0].message:
                model_output = response.choices[0].message.content
                start_index = model_output.find('{')
                end_index = model_output.rfind('}') + 1
                if start_index != -1 and end_index != -1 and start_index < end_index:
                    json_string = model_output[start_index:end_index]
                    parsed_json = json.loads(json_string)
                    if parsed_json.get("summary"):
                        company.detailed_descrption = parsed_json.get("summary")
                    if parsed_json.get("problem_statement"):
                        company.problem_statement = parsed_json.get("problem_statement")
                    if parsed_json.get("customer_list"):
                        company.customer_list = parsed_json.get("customer_list")

                    company.save()
                    break
        except Exception as e:
            logger.error(e)

def get_company_details(domain):
    messages = [
    {
        "role": "system",
        "content": ("You are Marketing expert, research and provide useful detailed information about the company, what they do, Problem they are solving, Customer list/type"),
    },
    {
        "role": "user",
        "content": "Go through " +domain + "and tell me more about the company, including what problem they solve, their customer's biggest challenges and customer list ",
    },
    ]

    perplexity_client = OpenAI(api_key="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", base_url="https://api.perplexity.ai")

    # chat completion without streaming
    response = perplexity_client.chat.completions.create(
        model="llama-3-sonar-large-32k-online",
        messages=messages,
    )

    return response.choices[0].message.content

def get_all_links(url, base_domain, max_depth, current_depth=0, visited=None):
    if visited is None:
        visited = set()
    
    if current_depth > max_depth or url in visited:
        return []

    visited.add(url)
    links = []
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(url, href)
            link_domain = urlparse(full_url).netloc
            if  not link_domain.startswith('docs.') and 'docs' not in full_url and 'learn' not in full_url and base_domain in full_url:
                title = a_tag.get('title') if a_tag.get('title') else a_tag.text.strip()
                links.append({'href': full_url, 'title': title})
                links.extend(get_all_links(full_url, base_domain, max_depth, current_depth + 1, visited))
    except Exception as e:
        logger.error(f"Request failed: {e}")
    
    return links

def format_links(domains):
    for i in range(2):
        try:
            response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                "role": "system",
                "content": [
                    {
                    "type": "text",
                    "text": "Categorize the links given below into the following categories:\n\nReturn Format Json\n{\n\"customer_case_study\": ### array of links,\n\"product_features\": ### array of links,\n\"news\": ### news update related to company,\n\"others\" ## array of remaining links\n}\n"
                    }
                ]
                },
                {
                "role": "user",
                "content": [
                    {
                    "type": "text",
                    "text": domains
                    }
                ]
                }
            ],
            temperature=1,
            max_tokens=2000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
            )

            if len(response.choices)>0 and response.choices[0].message:
                model_output = response.choices[0].message.content
                start_index = model_output.find('{')
                end_index = model_output.rfind('}') + 1
                if start_index != -1 and end_index != -1 and start_index < end_index:
                    json_string = model_output[start_index:end_index]
                    parsed_json = json.loads(json_string)
                    return parsed_json
        except Exception as e:
            logger.error(e)
 
    return None

def get_case_study(url, company):
    text = None
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes

        # Parse the HTML content of the page
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract all text from the page
        text = soup.get_text(separator=' ', strip=True)
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred: {e}")
        return None
    
    if text:
        for i in range(2):
            try:
                response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                        {
                        "role": "system",
                        "content": [
                            {
                            "type": "text",
                            "text": "Format the following details about the company from details provided and return json structure\n\nreturn Json \n\n{\n\"name\": ## name for a case study,\n\"summary\": ### summary of the case study,\n\"problem_statement\": ### major problem of the customer shown in the case study,\n\"customer_comment\": ### return a dict {\n             \"commentor\": ## name -title of person commented,\n              \"comment\": ### comment by the person},\n\"impact\": ### key metrics/impact that case study shows, try to give impact in numbers/percentage,\n\"customers_name\": ## customer in the case study (company name, keep it null if no name is mentioned),\n\"customer_type\": #### sentence defining the customer type, industry, size, any other parameters, don't be to specific, it should broader segment of companies\n}"
                            }
                        ]
                        },
                        {
                        "role": "user",
                        "content": [
                            {
                            "type": "text",
                            "text": text
                            }
                        ]
                        }
                    ],
                temperature=1,
                max_tokens=1169,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
                )
                if len(response.choices)>0 and response.choices[0].message:
                    model_output = response.choices[0].message.content
                    start_index = model_output.find('{')
                    end_index = model_output.rfind('}') + 1
                    if start_index != -1 and end_index != -1 and start_index < end_index:
                        json_string = model_output[start_index:end_index]
                        parsed_json = json.loads(json_string)
                        if parsed_json.get("impact"):
                            case_study=CaseStudy.objects.create(name=parsed_json.get("name", "NA"), summary= parsed_json.get("summary", None),
                                                    company=company, customer_comment=parsed_json.get("customer_comment", None),
                                                    problem_statement=parsed_json.get("problem_statement", None), impact=str(parsed_json.get("impact", "")),
                                                    customers_name=parsed_json.get("customers_name", None), customer_type=parsed_json.get("customer_type", None),
                                                    link=url)
                            break
            except Exception as e:
                logger.error(e, parsed_json)
    
def get_crunchbase_url(data):
    # Access the list of profiles from the dictionary
    profiles = data.get('profiles', [])
    
    for profile in profiles:
        if 'crunchbase.com/organization/' in profile:
            return profile
    return None

def get_all_post_detail(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    content_element = soup.select_one('p.attributed-text-segment-list__content')
    content = content_element.get_text(strip=True) if content_element else None

    # Extract the page URL safely
    by_element = soup.select_one('h1.section-title')
    by = by_element.get_text().strip().replace("’s Post", "") if by_element else None

    # Extract time safely
    time_element = soup.find('time')
    time = time_element.get_text().strip() if time_element else None

    # Extract reactions safely
    reactions_element = soup.find('span', {'data-test-id': 'social-actions__reaction-count'})
    reactions = reactions_element.get_text().strip() if reactions_element else None

    return content, by, time, reactions

#### mostly for posts 
def get_linkedin_current_data(linkedin_url):
    url = "https://piloterr.com/api/v2/linkedin/company/info?query=" + linkedin_url

    headers = {"x-api-key": "41d4da1b-344c-4be8-830a-a21374d494d4"}

    response = requests.request("GET", url, headers=headers)

    data = response.json()

    if data.get('posts'):
        posts = data.get('posts')
        for post in posts:
            content, by, time, reactions = get_all_post_detail(post['post_url'])
            post['content'] = content
            post['by'] = by
            post['when_posted'] = time
            post['reactions'] = reactions
        
        data['posts'] = posts

    return data


@shared_task
def create_personalised_email(id):
    email_personalisation = EmailMailPersonalisation.objects.get(id=id)
    client_search = PDLPY(
    api_key=settings.PEOPLE_DATA_LABS_API_KEY,
    )
    PARAMS = {
    "profile": [email_personalisation.person_linkedin_url]
    }

    person_data = client_search.person.enrichment(**PARAMS).json()
    email_personalisation.raw_person_data= person_data

    company_linkedin_url = None

    if person_data['data'].get('job_company_linkedin_url'):
        company_linkedin_url = "https://www." + person_data['data'].get('job_company_linkedin_url')

    PARAMS = {
    "website": email_personalisation.company_domain
    }
    crunch_base_url = None

    company_data = client_search.company.enrichment(**PARAMS).json()
    email_personalisation.raw_company_data= company_data
    company_post_data = None
    if company_data.get('status') == 200:
        if company_data.get('linkedin_id'):
            company_linkedin_url = 'https://www.linkedin.com/company/' + company_data.get('linkedin_id')
        
        crunch_base_url = get_crunchbase_url(company_data)
    
    if crunch_base_url:
        pass
        ## get more

    if company_linkedin_url:
        company_post_data = get_linkedin_current_data(company_linkedin_url)
    
    email_personalisation.company_post_data = company_post_data

    company_name = email_personalisation.email_sequence.company.name
    company_summary = email_personalisation.email_sequence.company.description
    company_key_problem = json.dumps(email_personalisation.email_sequence.company.problem_statement, indent=4)
    prospect_name = person_data['data'].get('first_name', 'NA')
    prospect_role = person_data['data'].get('job_title', 'NA')
    prospect_company = company_post_data.get('company_name', 'NA')
    prospect_summary = company_post_data.get('description', 'NA')
    base_emails = json.dumps(email_personalisation.email_sequence.email_json)

    email_personalisation.full_name = person_data['data'].get('full_name', 'NA')
    email_personalisation.company_name = prospect_company
    email_personalisation.title = prospect_role
    email_personalisation.save()



    if company_post_data and company_post_data.get("posts"):
        posts = get_post_relatability(company_post_data.get("posts"), company_name, company_summary, company_key_problem,
                                       prospect_company, prospect_summary)
        
        if isinstance(posts, dict) and posts.get('posts', []):
            posts = posts.get("posts")
        
        high_rated_posts = [post for post in posts if post['rating'] == 'high']
        personalised_email_copy = email_personalisation.personalised_email_copy

        if high_rated_posts:
            for post in high_rated_posts:
                mail = get_personalised_mail(company_name,company_summary,company_key_problem, prospect_name, prospect_role, prospect_company, 
                                             base_emails, post['content'])
                mail["reference_post"] = post.get("post_url", None)
                personalised_email_copy.append(mail)
        
        else:
            medium_rated_posts = [post for post in posts if post['rating'] == 'medium']
            for post in medium_rated_posts:
                mail = get_personalised_mail(company_name,company_summary,company_key_problem, prospect_name, prospect_role, prospect_company, 
                                             base_emails, post['content'])
                mail["reference_post"] = post.get("post_url", None) 
                personalised_email_copy.append(mail)
        
        email_personalisation.personalised_email_copy = personalised_email_copy

        
    else:
        email_personalisation.post_found=False
    

    email_personalisation.sequence_completed = True
    email_personalisation.save()
        

