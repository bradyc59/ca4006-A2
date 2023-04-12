from typing import List
from pydantic import BaseModel, BaseSettings
import logging
from fastapi import FastAPI, Request
import fastapi
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import pandas
from datetime import date, timedelta
import os

cur_path = os.path.dirname(__file__)

class Settings(BaseSettings):
    app_name: str="Test"
    user: str=""

settings = Settings()    
app = FastAPI()
templates = Jinja2Templates(directory="templates/")
logger = logging.getLogger(__name__)

logged_in_user = {}


funding_agencies =  {'Irish Research Council': 1000000, 'Science Foundation Ireland': 1000000, 'European Council': 1000000}

props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')

for i, p in props.iterrows():
    if p['approved'] == True:
        current = p['funding_agency']
        funding_agencies[current] = funding_agencies[current] - p['funding_amount']

researcher_form = False
  
class ResearchProposal(BaseModel):
    acronym: str
    title: str
    description: str
    researchers: str
    funding_agency: str
    funding_amount: float
    approved: bool

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

@app.get("/proposal")
async def root(request: Request, response_class=HTMLResponse):
    print(logged_in_user)
    print(settings.user)
    print(settings)
    return templates.TemplateResponse('proposal.html', {'request': request, 'user': settings.user})

# Research proposal endpoint
@app.post("/submit_proposal")
def submit_proposal(data: dict):
    today = date.today()
    data['end_date'] = today + timedelta(days=3*30)
    data['remaining_budget'] = data['funding_amount']
    data['researchers'] = settings.user
    if data['funding_agency'] == 'Irish Research Council':
        props = pandas.read_csv(cur_path + '/csv_files/Irish_research_council.csv')
        current_agency = data['funding_agency']
        if int(data['funding_amount']) >= 200000 and int(data['funding_amount']) <= 500000:
            if funding_agencies[current_agency] - int(data['funding_amount']) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - int(data['funding_amount'])
                data['approved'] = True

        props = props.append(data, ignore_index = True)
        props.to_csv(cur_path + '/csv_files/Irish_research_council.csv')
    if data['funding_agency'] == 'Science Foundation Ireland':
        props = pandas.read_csv(cur_path + '/csv_files/science_foundation_ireland.csv')
        current_agency = data['funding_agency']
        if int(data['funding_amount']) >= 200000 and int(data['funding_amount']) <= 500000:
            if funding_agencies[current_agency] - int(data['funding_amount']) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - int(data['funding_amount'])
                data['approved'] = True

        props = props.append(data, ignore_index = True)
        props.to_csv(cur_path + '/csv_files/science_foundation_ireland.csv')
    if data['funding_agency'] == 'European Council':
        props = pandas.read_csv(cur_path + '/csv_files/european_council.csv')
        current_agency = data['funding_agency']
        if int(data['funding_amount']) >= 200000 and int(data['funding_amount']) <= 500000:
            if funding_agencies[current_agency] - int(data['funding_amount']) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - int(data['funding_amount'])
                data['approved'] = True

        props = props.append(data, ignore_index = True)
        props.to_csv(cur_path + '/csv_files/european_council.csv')
    if data['approved'] == True:
        proposals = pandas.read_csv(cur_path + '/csv_files/proposals.csv')
        all_props = pandas.read_csv(cur_path + '/csv_files/list_all_proposals.csv')
        proposals = proposals.append(data, ignore_index = True)
        all_props = all_props.append(data, ignore_index = True)
        proposals.to_csv(cur_path + '/csv_files/proposals.csv')
        all_props.to_csv(cur_path + '/csv_files/list_all_proposals.csv')
        return JSONResponse(content={"message": "Your proposal was approved!"})
    else:
        all_props = pandas.read_csv(cur_path + '/csv_files/list_all_proposals.csv')
        data['end_date'] = 'N/A'
        data['remaining_budget'] = 'N/A'
        all_props = all_props.append(data, ignore_index = True)
        all_props.to_csv(cur_path + '/csv_files/list_all_proposals.csv.csv')
        return JSONResponse(content={"message": "Your proposal was rejected, the funding amount must be between 200K and 500k, if it was the funding agency cannot afford the amount you are asking for."})

@app.get('/view_proposal')
async def view_proposals(request: Request):
    props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')
    all_props = pandas.read_csv(cur_path + '/csv_files/list_all_proposals.csv')
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')

    print(all_props)
    proposals = {}
    for i, value in users.iterrows():
        if users.loc[i, 'email'] == settings.user:
            logged_in_user = users.loc[i] 
    for i, value in all_props.iterrows():
        for user in all_props['researchers'].str.cat(sep=','):
            print(user)
            if settings.user == user:
                proposals[i] = value.to_dict()
    for i, value in props.iterrows():
        print(logged_in_user)
        if logged_in_user['usertype'] == 'University':
            proposals[i] = value.to_dict()
    print(proposals)
    return templates.TemplateResponse('approve_proposals.html', {'request': request, 'proposals': proposals})

# @app.get("/success")
# async def success(request: Request, approved: bool):
#     # Render the success page
#         return JSONResponse(content={"message": "Your proposal was approved!"})
#     # else:
#     #     return JSONResponse(content={"message": "Your proposal was rejected, the funding amount must be between 200K and 500k, if it was the funding agency cannot afford the amount you are asking for."})

@app.get('/signup')
def signup(request: Request):
    return templates.TemplateResponse('signup.html', context={'request': request})

@app.post('/signup-confirm')
def signup_confirm(user_details: dict, request: Request):
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    emails = users['email'].tolist()
    if user_details['email'] in emails:
        return {"message": "User already exists"}

    user = pandas.DataFrame([user_details])
    user['id'] = users.shape[0] + 1
    new_users = users.append(user, ignore_index=True)
    new_users.to_csv(cur_path + '/csv_files/users.csv')
    return login_check(user_details)

@app.get('/')
async def login(request: Request):
    return templates.TemplateResponse('login.html', context={'request': request})

@app.post('/login-check')
def login_check(user_data: dict):
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    ids = users['id'].tolist()
    emails = users['email'].tolist()
    passwords = users['password'].tolist()
    names = users['name'].tolist()
    usertype = users['usertype'].tolist()
    organization = users['organization'].tolist()

    i= 0
    print(user_data['email'])
    while i < len(emails):
        if user_data['email'] == emails[i] and user_data['password'] == passwords[i]:
            logged_in_user = {
                'id': ids[i],
                'name': names[i],
                'email': emails[i],
                'password': passwords[i],
                'usertype': usertype[i],
                'organization': organization[i],
            }
            settings.user = logged_in_user["email"]
            print(settings.user)
            print(settings)
            return {'message': 'Successfully '}
        i += 1
    return {"message": "User does not exist"}


# Research account management endpoints
@app.post("/add-reseacrher")
def create_account(researcher: dict):
    # TODO: Create a new research account
    print(researcher)
    list_researchers = []
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')
    for i, value in users.iterrows():
        if users.loc[i, 'email'] == researcher['email']:
            for j, value in props.iterrows():
                print(props.loc[j, 'id'])
                print(researcher['id'])
                if int(props.loc[j, 'id']) == int(researcher['id']):
                    list_researchers.append(props.loc[j, 'researchers'])
                    list_researchers.append(researcher['email'])
                    print(list_researchers)
                    props.at[j, 'researchers'] = list_researchers
                    print(props.loc[j, 'researchers'])
    props.to_csv(cur_path + '/csv_files/proposals.csv')
    return {"message": "Account created successfully"}

@app.get("/account/{account_id}")
def get_account(account_id: str):
    # TODO: Get details of a research account
    return {"message": f"Details of account {account_id}"}

@app.put("/account/{account_id}")
def update_account(account_id: str, researchers: List[str]):
    # TODO: Update researchers associated with a research account
    return {"message": f"Researchers for account {account_id} updated successfully"}

# Transaction management endpoints
@app.post("/create_transaction")
def create_transaction(transaction: Transaction):
    # TODO: Create a new transaction
    return {"message": "Transaction created successfully"}

@app.get("/transactions/{account_id}")
def get_transactions(account_id: str):
    # TODO: Get all transactions for a research account
    return {"message": f"All transactions for account {account_id}"}

