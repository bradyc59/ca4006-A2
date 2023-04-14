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

class ResearchProposal(BaseModel):
    acronym: str
    title: str
    description: str
    funding_amount: int
    approved: bool = False
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

class Transaction(BaseModel):
    date: date
    amount: int
    
class Login(BaseModel):
    email: str
    password: str

@app.post("/submit-proposal")
async def submit_proposal(data: ResearchProposal):
    result = await agency.approve_proposal(data, settings.user)
    return result

@app.get('/view_proposal')
async def view_proposals():
    props = pandas.read_csv(cur_path + '/csv_files/list_all_proposals.csv')
    props = props.loc[:, ~props.columns.str.contains('^Unnamed')]
    list_users = pandas.read_csv(cur_path + '/csv_files/user_project.csv')
    list_users = list_users.loc[:, ~list_users.columns.str.contains('^Unnamed')]
    proposals = props.to_dict('records')
    if len(proposals) != 0:
        # Merge the two dataframes based on the common column "title"
        merged_df = pandas.merge(props, list_users, on='title')

        # Group the merged dataframe by "title" and create a dictionary
        grouped_df = merged_df.groupby('title')
        proposal_dict = {}
        for title, group in grouped_df:
            proposal_dict[title] = group['email'].tolist()

        # Add the user list to each proposal dictionary
        for proposal in proposals:
            title = proposal.get('title', '')
            proposal['users'] = proposal_dict.get(title, [])

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
    if email == input_email and str(password) == str(input_password):
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
    list_researchers = []
    users = await asyncio.to_thread(pandas.read_csv, cur_path + '/csv_files/users.csv')
    list_users = await asyncio.to_thread(pandas.read_csv, cur_path + '/csv_files/user_project.csv')
    user = {}
    props = await asyncio.to_thread(pandas.read_csv, cur_path + '/csv_files/proposals.csv')
    for i, value in users.iterrows():
        if users.loc[i, 'email'] == researcher.email:
            for k, value in list_users.iterrows():
                if list_users.loc[k, 'lead'] == True:
                    for j, value in props.iterrows():
                        if props.loc[j, 'title'] == researcher.title:
                            user['title'] = researcher.title
                            user['email'] = researcher.email
                            user = pandas.DataFrame([user])
                            list_users = list_users.append(user, ignore_index=True)
                            await asyncio.to_thread(list_users.to_csv, cur_path + '/csv_files/user_project.csv')
                            return {"message": f"Successfully added {researcher.email} to project {researcher.title}"}
    return {"message": f"Could not add {researcher.email} to project {researcher.title}"}


@app.post("/delete-from-project")
async def delete_from_project(account: NewResearcher):
    users = await asyncio.to_thread(pandas.read_csv, cur_path + '/csv_files/users.csv')
    list_user = await asyncio.to_thread(pandas.read_csv, cur_path + '/csv_files/user_project.csv')

    for i, value in users.iterrows():
        if users.loc[i, 'email'] == settings.user:
            logged_in_user = users.loc[i]

    for j, user in list_user.iterrows():
        if user['email'] == account.email and user['title'] == account.title:
            list_user = list_user.drop(index=j)
            await asyncio.to_thread(list_user.to_csv, cur_path + '/csv_files/user_project.csv')
            return {"message": f"Deleted {account.email} from project {account.title}"}
        
    return {"message": f"User {account.email} is not a part of project {account.title}"}



@app.post("/create_transaction")
async def create_transaction(transaction: Transaction):
    result = await agency.transaction(transaction, settings.user)
    return result
    

if __name__ == '__main__':
    ports = [8000, 8001, 8002]  # list of port numbers
    for port in ports:
        uvicorn.run('research:app', host='localhost', port=port, reload=True)
