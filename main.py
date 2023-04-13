from typing import List
from pydantic import BaseModel, BaseSettings, Field
import logging
from fastapi import FastAPI, Request
import fastapi
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import pandas
from datetime import date, timedelta, datetime
from fastapi.middleware.cors import CORSMiddleware
import os
from uuid import UUID, uuid4

import uvicorn
import endpoints

cur_path = os.path.dirname(__file__)

class Settings(BaseSettings):
    app_name: str="Test"
    user: str=""

settings = Settings()    
app = FastAPI()
app.include_router(endpoints.read_router)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    
class Login(BaseModel):
    email: str
    password: str

@app.get("/proposal")
async def root():
    print(settings)
    return {"message": "user already assigned to another project"}

def submit_proposal(data: ResearchProposal):
    user_pro = {
        'email': "",
        'title': "",
        'lead': True
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
    elif data.funding_agency == 'Science Foundation Ireland':
        props = pandas.read_csv(cur_path + '/csv_files/science_foundation_ireland.csv')
        current_agency = data.funding_agency
        if int(data.funding_amount) >= 200000 and int(data.funding_amount) <= 500000:
            if funding_agencies[current_agency] - int(data.funding_amount) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - int(data.funding_amount)
                diction['approved'] = True

        props = props.append(diction, ignore_index = True)
        props.to_csv(cur_path + '/csv_files/science_foundation_ireland.csv')
    elif data.funding_agency == 'European Council':
        props = pandas.read_csv(cur_path + '/csv_files/european_council.csv')
        current_agency = data.funding_agency
        if int(data.funding_amount) >= 200000 and int(data.funding_amount) <= 500000:
            if funding_agencies[current_agency] - int(data.funding_amount) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - int(data.funding_amount)
                diction['approved'] = True

        props = props.append(diction, ignore_index = True)
        props.to_csv(cur_path + '/csv_files/european_council.csv')
    else:
        return {"message": "Please provide a funding"}
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
    return {"message": f"No proposals assigned to user {settings.user}"}

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
    return {"message": f"{settings.user}"}

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
        if user_data.email == emails[i] and str(user_data.password) == str(passwords[i]):
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
                    list_users.to_csv(cur_path + '/csv_files/user_project.csv')
                    props.to_csv(cur_path + '/csv_files/proposals.csv')
                    return {"message": f"Successfully added {researcher.email} to project {researcher.title}"}
    return {"message": f"Could not add {researcher.email} to project {researcher.title}"}

@app.post("/delete-from-project")
def delete_from_project(account: NewResearcher):
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    list_user = pandas.read_csv(cur_path + '/csv_files/user_project.csv')

    for i, value in users.iterrows():
        if users.loc[i, 'email'] == settings.user:
            logged_in_user = users.loc[i] 

    for j, user in list_user.iterrows():
        if list_user.loc[j, 'email'] == account.email and list_user.loc[j, 'title'] == account.title:
            list_user = list_user.drop(index=i)
            list_user.to_csv(cur_path + '/csv_files/user_project.csv')
            return {"message": f"Deleted {account.email} from project {account.title}"}
        
    return {"message": f"User {account.email} is not a part of project {account.title}"}

# Transaction management endpoints
@app.post("/create_transaction")
def create_transaction(transaction: Transaction):
    list_user = pandas.read_csv(cur_path + '/csv_files/user_project.csv')
    props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')

    transaction_dict = {
        'date': transaction.date,
        'amount': transaction.amount
    }
    for i, value in list_user.iterrows():
        if settings.user == list_user.loc[i, 'email']:
            for j, prop in props.iterrows():
                if list_user.loc[i, 'title'] == props.loc[j, 'title']:
                    current_proposal = props.loc[j]
                    props = props.drop(index=j)
    date_object = datetime.strptime(current_proposal['end_date'], '%Y-%m-%d').date()
    if date_object > transaction_dict['date']:
        if int(current_proposal['remaining_budget']) >= int(transaction_dict['amount']):
            current_proposal['remaining_budget'] = int(current_proposal['remaining_budget']) - int(transaction_dict['amount'])
            props = props.append(current_proposal, ignore_index=True)
            props.to_csv(cur_path + '/csv_files/proposals.csv')
            with open(cur_path + '/transaction_files/transactions.txt', 'a') as f:
                    f.write(f"{settings.user} withdrew {transaction_dict['amount']} on {transaction_dict['date']} from {current_proposal['title']}, leaving the project with a total of {current_proposal['remaining_budget']} left. \n")
            return {"message": f"{settings.user} successfully completed a transaction withdrawing {transaction_dict['amount']} from {current_proposal['title']}"}
        else:
            return {"message": f"Insufficent budget left in project {current_proposal['title']}, remaining budget is {current_proposal['remaining_budget']}"}
    else:
        return {"message": f"Project {current_proposal['title']} is past the end date, the project ceased on {current_proposal['end_date']}"}

@app.get("/transaction")
def get_transactions(researcher: NewResearcher):
    # TODO: Get all transactions for a research account
    return {"message": f"All transactions for account {researcher}"}

if __name__ == '__main__':
    uvicorn.run('main:app', host="localhost", port=8005, reload=True)