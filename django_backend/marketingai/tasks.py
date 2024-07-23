from celery import shared_task
from openai import OpenAI
from django.conf import settings
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from marketingai.models import CaseStudy, Company
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
                            "text": "Format the following details about the company from details provided and return json structure\n\nreturn Json \n\n{\n\"name\": ## name for a case study,\n\"summary\": ### summary of the case study,\n\"problem_statement\": ### major problem of the customer shown in the case study,\n\"customer_comment\": ### return a dict {\n             \"commentor\": ## name -title of person commented,\n              \"comment\": ### comment by the person},\n\"impact\": ### key metrics/impact that case study shows,\n\"customers_name\": ## customer in the case study (company name, keep it null if no name is mentioned),\n\"customer_type\": #### sentence defining the customer type, industry, size, any other parameters, don't be to specific, it should broader segment of companies\n}"
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
    
