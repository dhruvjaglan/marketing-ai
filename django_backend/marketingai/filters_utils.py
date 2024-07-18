from marketingai.constants import TITLE_LIST
from fuzzywuzzy import process
from peopledatalabs import PDLPY
from marketingai.utils import fix_industries

def get_min_max_avg_funding(target_stages):
    funding_data = {
        "pre-seed": {"min": 100000, "max": 5000000, "average": 500000},
        "seed": {"min": 500000, "max": 10000000, "average": 4600000},
        "series-a": {"min": 2000000, "max": 50000000, "average": 18000000},
        "series-b": {"min": 10000000, "max": 100000000, "average": 35000000},
        "series-c": {"min": 20000000, "max": 200000000, "average": 50000000},
        "series-d+": {"min": 50000000, "max": 500000000, "average": 275000000}
    }

    min_funding = float('inf')
    max_funding = 0
    
    for stage in target_stages:
        if stage in funding_data.keys():
            stage_data = funding_data[stage]
            # Calculate the average if not provided
            avg_funding_temp = stage_data.get('average')
            min_funding_temp = stage_data.get('min')
            
            min_funding = min(min_funding, min_funding_temp)
            max_funding = max(max_funding, avg_funding_temp)
    
    if min_funding == float('inf') and max_funding == 0:
        return None, None  # No valid stages found
    else:
        return min_funding, max_funding
    

def get_min_max_size(target_categories):
    size_mapping = {
        "emerging": (0, 49),
        "small": (50, 200),
        "mid": (201, 1000),
        "large": (1001, 5000),
        "enterprise": (5001, 100000)
    }
    
    min_size = 100000
    max_size = 0
    
    for category in target_categories:
        if category.lower() in size_mapping:
            min_size = min(min_size, size_mapping[category][0])
            max_size = max(max_size, size_mapping[category][1])
    
    if min_size == float('inf') and max_size == 0:
        return None  # No valid categories found
    else:
        return min_size, max_size
    

def fix_location(location_string):
    CLIENT = PDLPY(
    api_key="25850d46eb1bddedbee51b93e8ebb9f44799500c26f157e6e423fc1058e6c15a",
    )

    # Create a parameters JSON object
    QUERY_STRING = {"location": location_string}

    # Pass the parameters object to the Location Cleaner API
    response = CLIENT.location.cleaner(**QUERY_STRING)
    data =response.json()

    if data['status']==200:
        return response.json()["region"], response.json()["country"]
    else:
        None, None 


def fix_titles(title_string):
    formatted_titles = process.extractBests(title_string, TITLE_LIST, score_cutoff=91, limit=6)
    
    return [title[0] for title in formatted_titles]


def fix_companies(company_string):
    CLIENT = PDLPY(
    api_key="25850d46eb1bddedbee51b93e8ebb9f44799500c26f157e6e423fc1058e6c15a",
    )

    # Create a parameters JSON object
    QUERY_STRING = {"name": company_string}

    response = CLIENT.company.cleaner(**QUERY_STRING)
    data =response.json()
    if data['status'] ==200:
        return data['name']
    else:
        None


def get_formatted_query(output):

    sql_query = "SELECT * FROM person WHERE "
    filters = {}
    queries = []
    if output.get('location') and isinstance(output.get('location'), list):
        regions = []
        countries = []
        for location in output.get('location'):
            region, country = fix_location(location)
            if region:
                regions.append(region)
            if country:
                countries.append(country)
        if countries:
            filters["location_country"] = countries
        if regions:
            filters["location_region"] = countries
        countries = list(set(countries))

        regions = list(set(regions))
        regions = ', '.join("'" + region.lower() + "'" for region in regions)
        countries = ', '.join("'" + country.lower() + "'" for country in countries)
        if regions:
            queries.append("location_region IN ("+ regions + ")")
        if countries:
            queries.append("location_country IN ("+ countries + ")")
    else:
        queries.append("location_country='united states'")
        filters["location_country"] = ['united states']

    if output.get('include_companies') or output.get('similar_companies'):
        companies = []
        if output.get('include_companies'):
            companies += output.get('include_companies')
        
        if output.get('similar_companies'):
            companies = output.get('similar_companies')
        formatted_companies=[]
        for company in companies:
            company = fix_companies(company)
            if company:
                formatted_companies.append(company)
        
        filters['job_company_name'] = formatted_companies
        
        formatted_companies = ', '.join("'" + company.lower() + "'" for company in formatted_companies)

        if formatted_companies:
            queries.append("job_company_name IN ("+ formatted_companies + ")")

    if output.get('exclude_companies') and isinstance(output.get('exclude_companies'), list):
        for company in output.get('exclude_companies'):
            formatted_companies=[]
            company = fix_companies(company)
            if company:
                formatted_companies.append(company)
            
            filters['not job_company_name'] = formatted_companies
            
            formatted_companies = ', '.join("'" + company.lower() + "'" for company in formatted_companies)

            if formatted_companies:
                queries.append("job_company_name NOT IN ("+ formatted_companies + ")")


    if output.get('job_title') and isinstance(output.get('job_title'), list):
        formatted_titles = []
        for title in output.get('job_title'):
            formatted_titles += fix_titles(title)
        formatted_titles = list(set(formatted_titles))
        filters['job_title'] = formatted_titles
        formatted_titles = ', '.join("'" + formatted_title.lower() + "'" for formatted_title in formatted_titles)

        if formatted_titles:
                queries.append("job_title IN ("+ formatted_titles + ")")

    if output.get('job_title_level') and isinstance(output.get('job_title_level'), list):
        formatted_level= []
        for job_title_level in output.get('job_title_level', []):
            if job_title_level.lower() in ['cxo', 'director', 'entry', 'manager', 'owner', 'partner', 'senior', 'training', 'unpaid', 'vp']:
                formatted_level.append(job_title_level.lower())
        
        filters['job_title_levels'] = formatted_level
        formatted_level = ', '.join("'" + level.lower() + "'" for level in formatted_level)

        if formatted_level:
            queries.append("job_title_levels IN ("+ formatted_level + ")")

    if output.get('job_roles') and isinstance(output.get('job_roles'), list):
        formatted_roles= []
        role_list  = [
                "advisory", "analyst", "creative", "education", "engineering", "finance", 
                "fulfillment", "health", "hospitality", "human_resources", "legal", 
                "manufacturing", "marketing", "operations", "partnerships", "product", 
                "professional_service", "public_service", "research", "sales", 
                "sales_engineering", "support", "trade"
            ]
        for role in output.get('job_roles'):
            if role.lower() in role_list:
                formatted_roles.append(role.lower())
        
        filters['job_title_role'] = formatted_roles
        formatted_roles = ', '.join("'" + role.lower() + "'" for role in formatted_roles)

        if formatted_roles:
            queries.append("job_title_role IN ("+ formatted_roles + ")")

    if output.get('company_size') and isinstance(output.get('company_size'), list):
        min, max = get_min_max_size(output.get('company_size'))
        filters['job_company_employee_count'] = (min, max)

        if max < 100000:
            
            queries.append("job_company_employee_count < "+ str(max))

        if min > 0:
            queries.append("job_company_employee_count > "+ str(min))

    if output.get('company_funding_stage') and isinstance(output.get('company_funding_stage'), list):
        min, max = get_min_max_avg_funding(output.get('company_funding_stage'))

        filters['job_company_total_funding_raised'] = (min, max)
        

        if max < 50000001:
            queries.append("job_company_total_funding_raised < "+ str(float(max)))
        if min >0:
            queries.append("job_company_total_funding_raised > "+ str(float(min)))


    if output.get("industry") and isinstance(output.get('industry'), list):
        industries = fix_industries(output.get("industry"))
        filters['job_company_industry'] = industries
        industries = ', '.join("'" + industry.lower() + "'" for industry in industries)

        if industries:
            queries.append("job_company_industry IN ("+ industries + ")")


    joined_queries= " AND ".join(queries)

    sql_query += joined_queries + ";"

    return filters, sql_query
