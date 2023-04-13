from fastapi import FastAPI

import pandas

import os

import uvicorn


cur_path = os.path.dirname(__file__)
 
app = FastAPI()

@app.get('/view_proposal')
async def view_proposals():
    props = pandas.read_csv(cur_path + '/csv_files/proposals.csv')

    proposals = []
    for i, value in props.iterrows():
        proposals.append(value.to_dict())

    print(proposals)
    if len(proposals) != 0:
        return {"proposals": proposals}

    return {"message": f"No proposals have been submitted to DCU"}

if __name__ == '__main__':
    uvicorn.run('dcu:app', host="localhost", port=8002, reload=True)