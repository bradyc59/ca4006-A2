import io
import math
from typing import List
import aiofiles
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


cur_path = os.path.dirname(__file__)


class Settings(BaseSettings):
    app_name: str = "Test"
    user: str = ""


settings = Settings()
app = FastAPI()
templates = Jinja2Templates(directory="templates/")
logger = logging.getLogger(__name__)

logged_in_user = {'email': settings.user}


funding_agencies = {'Irish Research Council': 1000000,
                    'Science Foundation Ireland': 1000000, 'European Council': 1000000}

props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')

for i, p in props.iterrows():
    if p['approved'] == True:
        current = p['funding_agency']
        funding_agencies[current] = funding_agencies[current] - \
            p['funding_amount']

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
    researcher: str
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
    name: str
    password: str
    budget: int


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
    name: str
    password: str


def approve_proposal(data: ResearchProposal, user: str):
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
        props = pandas.read_csv(
            cur_path + '/csv_files/Irish_research_council.csv')
        current_agency = data.funding_agency
        if int(data.funding_amount) >= 200000 and int(data.funding_amount) <= 500000:
            if funding_agencies[current_agency] - int(data.funding_amount) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - \
                    int(data.funding_amount)
                diction['approved'] = True

        props = props.append(diction, ignore_index=True)
        props.to_csv(cur_path + '/csv_files/Irish_research_council.csv')
    elif data.funding_agency == 'Science Foundation Ireland':
        props = pandas.read_csv(
            cur_path + '/csv_files/science_foundation_ireland.csv')
        current_agency = data.funding_agency
        if int(data.funding_amount) >= 200000 and int(data.funding_amount) <= 500000:
            if funding_agencies[current_agency] - int(data.funding_amount) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - \
                    int(data.funding_amount)
                diction['approved'] = True

        props = props.append(diction, ignore_index=True)
        props.to_csv(cur_path + '/csv_files/science_foundation_ireland.csv')
    elif data.funding_agency == 'European Council':
        props = pandas.read_csv(cur_path + '/csv_files/european_council.csv')
        current_agency = data.funding_agency
        if int(data.funding_amount) >= 200000 and int(data.funding_amount) <= 500000:
            if funding_agencies[current_agency] - int(data.funding_amount) >= 0:
                funding_agencies[current_agency] = funding_agencies[current_agency] - \
                    int(data.funding_amount)
                diction['approved'] = True

        props = props.append(diction, ignore_index=True)
        props.to_csv(cur_path + '/csv_files/european_council.csv')
    else:
        return {"message": "Please provide a funding"}
    if diction['approved'] == True:
        proposals = pandas.read_csv(cur_path + '/csv_files/proposals.csv')
        all_props = pandas.read_csv(
            cur_path + '/csv_files/list_all_proposals.csv')
        list_users = pandas.read_csv(cur_path + '/csv_files/user_project.csv')
        for i, value in list_users.iterrows():
            print("user: ", settings.user)
            print("list: ", list_users['email'].to_list())
            if user not in list_users['email'].to_list():
                print(123)
                user_pro['title'] = data.title
                user_pro['email'] = user
            else:
                return {"message": "user already assigned to another project"}
        proposals = proposals.append(diction, ignore_index=True)
        all_props = all_props.append(diction, ignore_index=True)
        print(user_pro)
        list_users = list_users.append(user_pro, ignore_index=True)
        list_users.to_csv(cur_path + '/csv_files/user_project.csv')
        proposals.to_csv(cur_path + '/csv_files/proposals.csv')
        all_props.to_csv(cur_path + '/csv_files/list_all_proposals.csv')
        return {"message": "Your proposal was approved!"}
    else:
        all_props = pandas.read_csv(
            cur_path + '/csv_files/list_all_proposals.csv')
        data.end_date = 'N/A'
        data.remaining_budget = 'N/A'
        all_props = all_props.append(diction, ignore_index=True)
        all_props.to_csv(cur_path + '/csv_files/list_all_proposals.csv.csv')
        return {"message": "Your proposal was rejected, the funding amount must be between 200K and 500k, if it was the funding agency cannot afford the amount you are asking for."}


@app.post('/signup-confirm')
async def signup_confirm(user_details: SignUp):
    async with aiofiles.open(cur_path + '/csv_files/funding_agency_login.csv', mode='r') as f:
        users = await pandas.read_csv(io.StringIO(await f.read()))

    names = users['name'].tolist()
    if user_details.name in names:
        return {"message": "User already exists"}

    user_details = {
        'name': user_details.name,
        'password': user_details.password,
        'budget': user_details.budget
    }
    user = pandas.DataFrame([user_details])
    new_users = users.append(user, ignore_index=True)

    async with aiofiles.open(cur_path + '/csv_files/funding_agency_login.csv', mode='w') as f:
        await f.write(new_users.to_csv(index=False))

    return {"message": f"Succesfully created funding agency: {user_details['name']}"}



@app.get('/')
async def login():
    return {"message": f"{settings.user}"}


@app.post('/login-check')
async def login_check(user_data: Login):
    async with aiofiles.open(cur_path + '/csv_files/funding_agency_login.csv', mode='r') as f:
        users = await pandas.read_csv(io.StringIO(await f.read()))

    names = users['name'].tolist()
    passwords = users['password'].tolist()
    budget = users['budget'].tolist()

    for i, name in enumerate(names):
        if user_data.name == name and user_data.password == passwords[i]:
            logged_in_user = {
                'name': name,
                'password': passwords[i],
                'budget': budget[i],
            }
            settings.user = logged_in_user['name']
            return {'message': f'Successfully logged in as {settings.user}'}

    return {"message": "User does not exist"}


@app.get('/view_proposal')
async def view_proposals():
    all_props = pandas.read_csv(cur_path + '/csv_files/list_all_proposals.csv')
    users = pandas.read_csv(cur_path + '/csv_files/funding_agency_login.csv')
    list_user = pandas.read_csv(cur_path + '/csv_files/user_project.csv')
    proposals = {
        'acronym': '',
        'title': '',
        'description': '',
        'researchers': '',
        'funding_agency': '',
        'approved': '',
        'funding_amount': '',
        'end_date': '',
        'remaining_budget': ''
    }
    list_researcher = []
    proposal_dict = []

    for i, value in all_props.iterrows():
        for j, user in list_user.iterrows():
            if all_props.loc[i, 'funding_agency'] == settings.user:
                if list_user.loc[j, 'title'] == all_props.loc[i, 'title']:
                    list_researcher.append(list_user.loc[j, 'email'])
            proposals = all_props.loc[i]
            proposals['researchers'] = list_researcher
            proposal_dict.append(proposals)

    print(proposal_dict)
    if len(proposal_dict) != 0:
        return {"proposals": proposal_dict[0]}

    return {"message": f"No proposals assigned to funding agency: {settings.user}"}

if __name__ == '__main__':
    uvicorn.run('agency:app', host="localhost", port=8001, reload=True)
