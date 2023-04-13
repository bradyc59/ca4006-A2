import asyncio
import io
import math
from typing import List
import aiofiles
import httpx
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
import dcu
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


funding_agencies = {'Irish Research Council': 1000000}

props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')

# for i, p in props.iterrows():
#     if p['approved'] == True:
#         current = p[0]
#         funding_agencies[current] = funding_agencies[current] - p['funding_amount']

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
    funding_amount: int
    approved: bool = False
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

@app.post('/approve_proposal')
async def approve_proposal(data: ResearchProposal, user: str):
    print('agency: ', data)
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
        'end_date': data.end_date,
        'remaining_budget': data.remaining_budget
    }
    if int(data.funding_amount) >= 200000 and int(data.funding_amount) <= 500000:
        if list(funding_agencies.values())[0] - int(data.funding_amount) >= 0:
                list(funding_agencies.values())[0] = list(funding_agencies.values())[0] - int(data.funding_amount)
                diction['approved'] = True

    if diction['approved'] == True:
        loop = asyncio.get_event_loop()
        print("Hello from agency",user)
        result = await loop.run_in_executor(None, dcu.approved_proposal, diction, user)
        return result
    else:
        all_props = pandas.read_csv(
            cur_path + '/csv_files/list_all_proposals.csv')
        data.end_date = 'N/A'
        data.remaining_budget = 'N/A'
        all_props = all_props.append(diction, ignore_index=True)
        all_props.to_csv(cur_path + '/csv_files/list_all_proposals.csv.csv')
        return {"message": "Your proposal was rejected, the funding amount must be between 200K and 500k, if it was the funding agency cannot afford the amount you are asking for."}

@app.get('/view_proposal')
async def view_proposals():
    props = pandas.read_csv(cur_path + '/csv_files/list_all_proposals.csv')
    props = props.loc[:, ~props.columns.str.contains('^Unnamed')]
    print(props)
    proposals = []
    for i, value in props.iterrows():
        proposals.append(props.loc[i].to_dict())
    if len(proposals) != 0:
        return {"proposals": proposals}

    return {"message": f"No proposals have been submitted to your agency"}

if __name__ == '__main__':
    uvicorn.run('agency:app', host="localhost", port=8003, reload=True)
