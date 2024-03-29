from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from .features.git import Git
import requests
from bs4 import BeautifulSoup
import os
import json
from enum import Enum

app = FastAPI()

origins = json.loads(os.getenv('CORS_ORIGINS'))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
@app.head("/")
async def root():
    git = Git()
    return {
        "git": git.short_hash(),
        "message": "Hello World",
        "time": datetime.utcnow()
    }

@app.get("/health-check")
def health_check():
    return "success"


class RaceDateEnum(Enum):
    LAST = 1
    NEXT = 2


def get_soup(url):
    response = requests.get(url)
    response.encoding = 'windows-1250'
    return BeautifulSoup(response.text, 'html.parser')


def get_league_url():
    return os.getenv('LEAGUE_URL') or 'https://vcbl.firesport.eu'


def get_race_url(race_date: RaceDateEnum):
    # Download league webpage
    soup = get_soup(get_league_url())

    # Select race's link from table
    if race_date == RaceDateEnum.LAST:
        link = soup.select_one('#tablygsou1 td:nth-child(2) a')
    elif race_date == RaceDateEnum.NEXT:
        link = soup.select_one('#tabkallig td:nth-child(3) > a')
    else:
        return None

    if link is not None:
        return get_league_url() + '/' + link.get("href").replace("soutez", "vysledek")
    return None


def get_data_from_url(url):
    soup = get_soup(url)

    tables = {
        'muzi': '#tab1151',
        'zeny': '#tab124',
        'veterani': '#tab1104',
        'dorostenci': '#tab184'
    }

    for table_key in tables.keys():
        table = soup.select(tables[table_key])
        if len(table) == 0:
            tables[table_key] = []
            continue

        table = table[0]
        table_data = []
        # headers = [header.text.strip() for header in table.find_all('th')]
        headers = []
        for header in table.find_all('th'):
            h = header.text.strip()
            if h == 'Tým a jméno':
                h = 'team'
            elif h == 'Okr.':
                h = 'district'
            elif h == 'Poř.':
                h = 'place'
            elif h == 'Výs.čas':
                h = 'final_time'
            elif h == 'Media':
                h = 'media'
            elif h == "1":
                h = "left_time"
            elif h == "2":
                h = "right_time"
            headers.append(h)

        rows = table.find_all('tr')
        for row in rows[1:]:
            cells = row.find_all('td')
            row_data = [cell.text.strip() for cell in cells]
            table_data.append(dict(zip(headers, row_data)))

        tables[table_key] = table_data

    return tables

@app.get('/results/{url}')
def results(url: str):
    if url == "next":
        data = get_data_from_url(get_race_url(RaceDateEnum.NEXT))
    elif url == "last":
        data = get_data_from_url(get_race_url(RaceDateEnum.LAST))
    else:
        data = get_data_from_url(f'{get_league_url()}/{url}')

    if not data:
        return {}
    return data

@app.get('/results')
def results_without_url():
    return results("last")
