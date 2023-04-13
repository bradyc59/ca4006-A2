from datetime import date, timedelta
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

if __name__ == '__main__':
    uvicorn.run('dcu:app', host="localhost", port=8004, reload=True)