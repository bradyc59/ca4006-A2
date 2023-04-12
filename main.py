from typing import List
from pydantic import BaseModel, BaseSettings, Field
import logging
from fastapi import FastAPI, Request
import fastapi
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import pandas
from datetime import date, timedelta
import os
from uuid import UUID, uuid4

cur_path = os.path.dirname(__file__)

class Settings(BaseSettings):
    app_name: str="Test"
    user: str=""

settings = Settings()    
app = FastAPI()
templates = Jinja2Templates(directory="templates/")
logger = logging.getLogger(__name__)

logged_in_user = { 'email': settings.user }


funding_agencies =  {'Irish Research Council': 1000000, 'Science Foundation Ireland': 1000000, 'European Council': 1000000}

props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')

for i, p in props.iterrows():
    if p['approved'] == True:
        current = p['funding_agency']
        funding_agencies[current] = funding_agencies[current] - p['funding_amount']

researcher_form = False
today = date.today()
  
class ResearchProposal(BaseModel):
    acronym: str
    title: str
    description: str
    funding_agency: str
    funding_amount: int
    approved: bool
    remaining_budget: int
    end_date: str = today + timedelta(days=3*30)

class NewResearcher(BaseModel):
    title: str
    email: str

class SignUp(BaseModel):
    email: str
    password: str
    usertype: str
    organization: str = "None"

class ResearchAccount(BaseModel):
    id: int
    researchers: List[str] = []
    approved_proposal: str
    remaining_budget: int
    end_date: date

class Transaction(BaseModel):
    date: date
    amount: int
    account_id: int

class Login(BaseModel):
    email: str
    password: str

@app.get("/proposal")
async def root():
    print(settings)
    return {"message": "user already assigned to another project"}

# Research proposal endpoint
@app.post("/submit_proposal")
def submit_proposal(data: ResearchProposal):
    user_pro = {
        'email': "",
        'title': ""
    }
    diction = {
            'acronym': data.acronym,
            'title': data.title,
            'description': data.description,
            'funding_amount': data.funding_amount,
            'approved': data.approved,
            'funding_agency': data.funding_agency,
            'end_date': data.end_date,
            'remaining_budget': data.remaining_budget
        }
    print(data)
    if data.funding_agency == 'Irish Research Council':
        props = pandas.read_csv(cur_path + '/csv_files/Irish_research_council.csv')
        current_agency = data.funding_agency
        if int(data.funding_amount) >= 200000 and int(data.funding_amount) <= 500000:
            if funding_agencies[current_agency] - int(data.funding_amount) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - int(data.funding_amount)
                diction['approved'] = True
        
        props = props.append(diction, ignore_index = True)
        props.to_csv(cur_path + '/csv_files/Irish_research_council.csv')
    if data.funding_agency == 'Science Foundation Ireland':
        props = pandas.read_csv(cur_path + '/csv_files/science_foundation_ireland.csv')
        current_agency = data.funding_agency
        if int(data.funding_amount) >= 200000 and int(data.funding_amount) <= 500000:
            if funding_agencies[current_agency] - int(data.funding_amount) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - int(data.funding_amount)
                diction['approved'] = True

        props = props.append(diction, ignore_index = True)
        props.to_csv(cur_path + '/csv_files/science_foundation_ireland.csv')
    if data.funding_agency == 'European Council':
        props = pandas.read_csv(cur_path + '/csv_files/european_council.csv')
        current_agency = data.funding_agency
        if int(data.funding_amount) >= 200000 and int(data.funding_amount) <= 500000:
            if funding_agencies[current_agency] - int(data.funding_amount) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - int(data.funding_amount)
                diction['approved'] = True

        props = props.append(diction, ignore_index = True)
        props.to_csv(cur_path + '/csv_files/european_council.csv')
    if diction['approved'] == True:
        proposals = pandas.read_csv(cur_path + '/csv_files/proposals.csv')
        all_props = pandas.read_csv(cur_path + '/csv_files/list_all_proposals.csv')
        list_users = pandas.read_csv(cur_path + '/csv_files/user_project.csv')
        for i, value in list_users.iterrows():
            print("user: ", settings.user)
            print("list: ", list_users['email'].to_list())
            if settings.user not in list_users['email'].to_list():
                print(123)
                user_pro['title'] = data.title
                user_pro['email'] = settings.user
            else:
                return {"message": "user already assigned to another project"}
        proposals = proposals.append(diction, ignore_index = True)
        all_props = all_props.append(diction, ignore_index = True)
        print(user_pro)
        list_users = list_users.append(user_pro, ignore_index = True)
        list_users.to_csv(cur_path + '/csv_files/user_project.csv')
        proposals.to_csv(cur_path + '/csv_files/proposals.csv')
        all_props.to_csv(cur_path + '/csv_files/list_all_proposals.csv')
        return {"message": "Your proposal was approved!"}
    else:
        all_props = pandas.read_csv(cur_path + '/csv_files/list_all_proposals.csv')
        data.end_date = 'N/A'
        data.remaining_budget = 'N/A'
        all_props = all_props.append(diction, ignore_index = True)
        all_props.to_csv(cur_path + '/csv_files/list_all_proposals.csv.csv')
        return {"message": "Your proposal was rejected, the funding amount must be between 200K and 500k, if it was the funding agency cannot afford the amount you are asking for."}

@app.get('/view_proposal')
async def view_proposals():
    props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')
    all_props = pandas.read_csv(cur_path + '/csv_files/list_all_proposals.csv')
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    list_user = pandas.read_csv(cur_path + '/csv_files/user_project.csv')

    print(all_props)
    proposals = []
    list_researcher = []
    for i, value in users.iterrows():
        if users.loc[i, 'email'] == settings.user:
            logged_in_user = users.loc[i] 
    for i, value in props.iterrows():
        print(logged_in_user)
        if logged_in_user['usertype'] == 'University':
            proposals.append(value.to_dict())
            return {"proposals": proposals}

    for i, value in all_props.iterrows():
        for j, user in list_user.iterrows():
            if list_user.loc[j, 'title'] == all_props.loc[i, 'title']:
                print("Hello")
                list_researcher.append(list_user.loc[j, 'email'])
            
        proposal_dict = all_props.loc[i].to_dict()
        proposal_dict['researchers'] = list_researcher
        proposals.append(proposal_dict)
    if len(proposals) != 0:
        return {"proposals": proposals}


    print(proposals)
    return {"message": "user already assigned to another project"}

@app.get('/signup')
def signup(request: Request):
    return {"message": "user already assigned to another project"}

@app.post('/signup-confirm')
def signup_confirm(user_details: SignUp):
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    emails = users['email'].tolist()
    if user_details.email in emails:
        return {"message": "User already exists"}
    user_details = {
        'email': user_details.email,
        'password': user_details.password,
        'usertype': user_details.usertype,
        'organization': user_details.organization,
    }
    user = pandas.DataFrame([user_details])
    new_users = users.append(user, ignore_index=True)
    new_users.to_csv(cur_path + '/csv_files/users.csv')
    return {"message": f"Succesfully created user {user_details['email']}"}

@app.get('/')
async def login():
    return {"message": settings.user}

@app.post('/login-check')
def login_check(user_data: Login):
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    emails = users['email'].tolist()
    passwords = users['password'].tolist()
    usertype = users['usertype'].tolist()
    organization = users['organization'].tolist()

    i= 0
    print(user_data.email)
    print(emails)
    while i < len(emails):
        print(emails[i], passwords[i])
        if user_data.email == emails[i] and user_data.password == passwords[i]:
            logged_in_user = {
                'email': emails[i],
                'password': passwords[i],
                'usertype': usertype[i],
                'organization': organization[i],
            }
            settings.user = logged_in_user['email']
            print(settings.user)
            print(settings)
            return {'message': f'Successfully logged in as {settings.user}'}
        i += 1
    return {"message": "User does not exist"}


# Research account management endpoints
@app.post("/add-reseacrher")
def create_account(researcher: NewResearcher):
    # TODO: Create a new research account
    print(researcher)
    list_researchers = []
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    list_users = pandas.read_csv(cur_path + '/csv_files/user_project.csv')
    user = {}
    props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')
    for i, value in users.iterrows():
        if users.loc[i, 'email'] == researcher.email:
            for j, value in props.iterrows():
                if props.loc[j, 'title'] == researcher.title:
                    user['title'] = researcher.title
                    user['email'] = researcher.email
                    user = pandas.DataFrame([user])
                    list_users = list_users.append(user, ignore_index=True)
                    print(list_users)
                    list_users.to_csv(cur_path + '/csv_files/user_project.csv')
    props.to_csv(cur_path + '/csv_files/proposals.csv')
    return {"message": "Account created successfully"}

@app.post("/delete-from-project")
def delete_from_project(account: NewResearcher):
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    list_user = pandas.read_csv(cur_path + '/csv_files/user_project.csv')

    for i, value in users.iterrows():
        if users.loc[i, 'email'] == settings.user:
            logged_in_user = users.loc[i] 

    for j, user in list_user.iterrows():
        if list_user.loc[j, 'email'] == account.email and list_user.loc[j, 'title'] == account.title:
            print("Hello")
            list_user = list_user.drop(index=i)
            list_user.to_csv(cur_path + '/csv_files/user_project.csv')
            return {"message": f"Deleted  from project "}
        
    return {"message": f"User  not a part of "}

# Transaction management endpoints
@app.post("/create_transaction")
def create_transaction(transaction: Transaction):
    # TODO: Create a new transaction
    return {"message": "Transaction created successfully"}

@app.get("/transactions/{account_id}")
def get_transactions(account_id: str):
    # TODO: Get all transactions for a research account
    return {"message": f"All transactions for account {account_id}"}

