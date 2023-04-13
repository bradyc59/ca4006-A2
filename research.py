import asyncio
from typing import List
from pydantic import BaseModel, BaseSettings, Field
import logging
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import pandas
from datetime import date, timedelta, datetime
from fastapi.middleware.cors import CORSMiddleware
import os
import agency
from concurrent.futures import ThreadPoolExecutor
import aiofiles
import io

import uvicorn

cur_path = os.path.dirname(__file__)

class Settings(BaseSettings):
    app_name: str="Test"
    user: str=""

settings = Settings()    
app = FastAPI()
templates = Jinja2Templates(directory="templates/")
logger = logging.getLogger(__name__)

logged_in_user = { 'email': settings.user }

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

@app.post("/submit-proposal")
async def submit_proposal(data: ResearchProposal):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, agency.approve_proposal, data, settings.user)
    return result

from concurrent.futures import ThreadPoolExecutor

@app.get('/view_proposal')
async def view_proposals():
    with ThreadPoolExecutor() as executor:
        future = executor.submit(load_data)
        proposals = await future
    if len(proposals) != 0:
        return {"proposals": proposals}
    return {"message": f"No proposals assigned to user {settings.user}"}

def load_data():
    props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')
    all_props = pandas.read_csv(cur_path + '/csv_files/list_all_proposals.csv')
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    list_user = pandas.read_csv(cur_path + '/csv_files/user_project.csv')
    props = props.loc[:, ~props.columns.str.contains('^Unnamed')]
    all_props = all_props.loc[:, ~all_props.columns.str.contains('^Unnamed')]
    users = users.loc[:, ~users.columns.str.contains('^Unnamed')]
    list_user = list_user.loc[:, ~list_user.columns.str.contains('^Unnamed')]

    print(all_props)
    proposals = []
    list_researcher = []
    for i, value in all_props.iterrows():
        for j, user in list_user.iterrows():
            if list_user.loc[j, 'title'] == all_props.loc[i, 'title']:
                list_researcher.append(list_user.loc[j, 'email'])

        proposal_dict = all_props.loc[i].to_dict()
        proposal_dict['researchers'] = list_researcher
        proposals.append(proposal_dict)
    return proposals


@app.get('/signup')
def signup(request: Request):
    return {"message": "user already assigned to another project"}

import concurrent.futures

@app.post('/signup-confirm')
async def signup_confirm(user_details: SignUp):
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    emails = users['email'].tolist()
    if user_details.email in emails:
        return {"message": "User already exists"}

    # Define a function to write the new user details to file
    def write_user_details(user_details):
        user_details = {
            'email': user_details.email,
            'password': user_details.password,
            'usertype': user_details.usertype,
            'organization': user_details.organization,
        }
        user = pandas.DataFrame([user_details])
        new_users = users.append(user, ignore_index=True)
        new_users.to_csv(cur_path + '/csv_files/users.csv')

    # Execute the write operation asynchronously using threads
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(write_user_details, user_details)
        await future

    return {"message": f"Succesfully created user {user_details['email']}"}


@app.get('/')
async def login():
    return {"message": f"{settings.user}"}

@app.post('/login-check')
async def login_check(user_data: Login):
    users = pandas.read_csv(cur_path + '/csv_files/users.csv')
    emails = users['email'].tolist()
    passwords = users['password'].tolist()
    usertype = users['usertype'].tolist()
    organization = users['organization'].tolist()

    tasks = []
    for i, email in enumerate(emails):
        tasks.append(asyncio.create_task(check_user(email, passwords[i], usertype[i], organization[i], user_data.email, user_data.password)))
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, dict):
            logged_in_user = result
            settings.user = logged_in_user['email']
            return {'message': f'Successfully logged in as {settings.user}'}
    return {"message": "User does not exist"}


async def check_user(email, password, usertype, organization, input_email, input_password):
    if email == input_email and password == input_password:
        return {
            'email': email,
            'password': password,
            'usertype': usertype,
            'organization': organization,
        }
    return None

@app.post("/add-reseacrher")
async def create_account(researcher: NewResearcher):
    # TODO: Create a new research account
    print(researcher)
    list_researchers = []
    users = await asyncio.to_thread(pandas.read_csv, cur_path + '/csv_files/users.csv')
    list_users = await asyncio.to_thread(pandas.read_csv, cur_path + '/csv_files/user_project.csv')
    user = {}
    props = await asyncio.to_thread(pandas.read_csv, cur_path + '/csv_files/proposals.csv')
    for i, value in users.iterrows():
        if users.loc[i, 'email'] == researcher.email:
            for j, value in props.iterrows():
                if props.loc[j, 'title'] == researcher.title:
                    user['title'] = researcher.title
                    user['email'] = researcher.email
                    user = pandas.DataFrame([user])
                    list_users = list_users.append(user, ignore_index=True)
                    await asyncio.to_thread(list_users.to_csv, cur_path + '/csv_files/user_project.csv')
                    await asyncio.to_thread(props.to_csv, cur_path + '/csv_files/proposals.csv')
                    return {"message": f"Successfully added {researcher.email} to project {researcher.title}"}
    return {"message": f"Could not add {researcher.email} to project {researcher.title}"}


@app.post("/delete-from-project")
async def delete_from_project(account: NewResearcher):
    users = await asyncio.to_thread(pandas.read_csv, cur_path + '/csv_files/users.csv')
    list_users = await asyncio.to_thread(pandas.read_csv, cur_path + '/csv_files/user_project.csv')

    for i, value in users.iterrows():
        if users.loc[i, 'email'] == settings.user:
            logged_in_user = users.loc[i]

    for j, user in list_user.iterrows():
        if user['email'] == account.email and user['title'] == account.title:
            list_user = list_user.drop(index=j)
            await asyncio.to_thread(list_users.to_csv, cur_path + '/csv_files/user_project.csv')
            return {"message": f"Deleted {account.email} from project {account.title}"}
        
    return {"message": f"User {account.email} is not a part of project {account.title}"}



@app.post("/create_transaction")
async def create_transaction(transaction: Transaction):
    async with aiofiles.open(cur_path + '/csv_files/user_project.csv', mode='r') as f:
        list_user = await f.read()
    list_user = pandas.read_csv(io.StringIO(list_user))

    async with aiofiles.open(cur_path + '/csv_files/proposals.csv', mode='r') as f:
        props = await f.read()
    props = pandas.read_csv(io.StringIO(props))

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
            props.to_csv(cur_path + '/csv_files/proposals.csv', index=False)
            async with aiofiles.open(cur_path + '/transaction_files/transactions.txt', mode='a') as f:
                await f.write(f"{settings.user} withdrew {transaction_dict['amount']} on {transaction_dict['date']} from {current_proposal['title']}, leaving the project with a total of {current_proposal['remaining_budget']} left. \n")
            return {"message": f"{settings.user} successfully completed a transaction withdrawing {transaction_dict['amount']} from {current_proposal['title']}"}
        else:
            return {"message": f"Insufficient budget left in project {current_proposal['title']}, remaining budget is {current_proposal['remaining_budget']}"}
    else:
        return {"message": f"Project {current_proposal['title']} is past the end date, the project ceased on {current_proposal['end_date']}"}



@app.get("/transaction")
def get_transactions(researcher: NewResearcher):
    # TODO: Get all transactions for a research account
    return {"message": f"All transactions for account {researcher}"}

if __name__ == '__main__':
    uvicorn.run('research:app', host="localhost", port=8000, reload=True)