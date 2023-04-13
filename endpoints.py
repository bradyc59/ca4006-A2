from datetime import date, timedelta
import os
from fastapi import APIRouter, BackgroundTasks
import asyncio
import time
from fastapi import File, UploadFile
from pydantic import BaseModel
# import aiofiles
# import httpx
import main

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


read_router = APIRouter()
url_list = ['https://reddit.com', 'https://google.com', 'https://ru.wikipedia.org/',
            'https://www.youtube.com/', 'https://www.facebook.com/', 'https://www.instagram.com/',
            'https://www.twitch.tv/', 'https://www.yahoo.com/', 'https://www.amazon.com/']


async def run_in_process(fn, *args):
    """Run a function in a separate process"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn, *args)


#   CPU calculations
async def calculate_data_for_file(file) -> int:
    """A blocking CPU-bound function"""
    print('calculating with async')
    name = file.filename
    name_len = len(name)
    time.sleep(8)
    return name_len


def calculate_data_for_file_sync(file) -> int:
    print('calculating in sync')
    name = file.filename
    name_len = len(name)
    time.sleep(6)
    return name_len


#   Requests
async def send_request_through_httpx() -> float:
    """Non-blocking IO-bound function - sending network requests"""
    st = time.time()
    #await asyncio.sleep(5)
    # async with httpx.AsyncClient() as client:
    #     tasks = []
    #     for url in url_list:
    #         tasks.append(client.get(url))
    #     responses = await asyncio.gather(*tasks)
    #     for r in responses:
    #         print(r.status_code)

    # fin = time.time() - st
    # return fin


async def send_request_through_requests_sync() -> float:
    """Blocking IO-bound function - sending network requests"""
    st = time.time()
    # for url in url_list:
    #     r = httpx.get(url)  # same as requests.get(url)
    #     print(r.status_code)
    # fin = time.time() - st
    # return fin


#   File reading
def read_file_data_sync(file: UploadFile = File(...)) -> str:
    """Blocking IO-bound function - reading file"""
    print('reading file in sync')
    os.chdir('D:\\')
    with open(file.filename, 'r'):
        file.read()
        return 'done'


async def read_file_data(file: UploadFile = File(...)) -> str:
    """Non-blocking IO-bound function - reading file"""
    print('reading file async')
   # await asyncio.sleep(1)
    os.chdir('D:\\')
    # async with aiofiles.open(file.filename, mode='r'):
    #     await file.read()
    #     return 'done'



@read_router.post("/submit-proposal", tags=['Read files'],
                  description='Reads a file async '
                              'and runs CPU-bound task',
                  status_code=200)
# will block main thread
async def read_file_and_calculate(file: ResearchProposal):
    st = time.time()
    result = main.submit_proposal(file)
    time_taken = time.time() - st
    return {'filename': file, 'contents': result,'took': time_taken}