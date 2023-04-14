from datetime import date, timedelta, datetime
import io
import aiofiles
from fastapi import FastAPI

import pandas

import os
from pydantic import BaseModel

import uvicorn


cur_path = os.path.dirname(__file__)
today = date.today()
 
app = FastAPI()

class ResearchProposal(BaseModel):
    acronym: str
    title: str
    description: str
    funding_amount: int
    approved: bool = False
    remaining_budget: int
    end_date: str = today + timedelta(days=3*30)

class Transaction(BaseModel):
    date: date
    amount: int

@app.post('/approved_proposal')
def approved_proposal(diction: ResearchProposal, user: str):
    print('dcu: ', diction)

    user_pro = {
        'email': "",
        'title': "",
        'lead': True
    }

    all_props = pandas.read_csv(
            cur_path + '/csv_files/list_all_proposals.csv')
    list_users = pandas.read_csv(cur_path + '/csv_files/user_project.csv')
    proposals = pandas.read_csv(cur_path + '/csv_files/proposals.csv')
    for i, value in list_users.iterrows():
            print("user: ", user)
            print("list: ", list_users['email'].to_list())
            print(123)
            user_pro['title'] = diction['title']
            user_pro['email'] = user
    proposals = proposals.append(diction, ignore_index=True)
    all_props = all_props.append(diction, ignore_index=True)
    list_users = list_users.append(user_pro, ignore_index=True)
    list_users.to_csv(cur_path + '/csv_files/user_project.csv')
    proposals.to_csv(cur_path + '/csv_files/proposals.csv')
    all_props.to_csv(cur_path + '/csv_files/list_all_proposals.csv')
    return {"message": "Your proposal was approved!"}

@app.get('/view_proposal')
async def view_proposals():
    props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')
    props = props.loc[:, ~props.columns.str.contains('^Unnamed')]
    print(props)
    proposals = []
    for i, value in props.iterrows():
        proposals.append(props.loc[i].to_dict())
    if len(proposals) != 0:
        return {"proposals": proposals}

    return {"message": f"No proposals have been submitted to DCU"}

async def write_transaction(transaction: Transaction, user: str):
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
        if user == list_user.loc[i, 'email']:
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
                await f.write(f"{user} withdrew {transaction_dict['amount']} on {transaction_dict['date']} from {current_proposal['title']}, leaving the project with a total of {current_proposal['remaining_budget']} left. \n")
            return {"message": f"{user} successfully completed a transaction withdrawing {transaction_dict['amount']} from {current_proposal['title']}"}
        else:
            return {"message": f"Insufficient budget left in project {current_proposal['title']}, remaining budget is {current_proposal['remaining_budget']}"}
    else:
        return {"message": f"Project {current_proposal['title']} is past the end date, the project ceased on {current_proposal['end_date']}"}

@app.get('/view-transactions')
async def view_transactions():
    async with aiofiles.open(cur_path + '/transaction_files/transactions.txt', mode='r') as f:
        transactions = await f.readlines()
    return {'transactions': transactions}

if __name__ == '__main__':
    uvicorn.run('dcu:app', host="localhost", port=8004, reload=True)