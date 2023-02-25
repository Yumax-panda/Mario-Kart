from typing import Optional, Union

from google.oauth2 import service_account
from google.cloud import storage
from google.cloud.exceptions import NotFound
from oauth2client.service_account import ServiceAccountCredentials
import gspread

from datetime import datetime
from zoneinfo import ZoneInfo
import aiohttp
import json
import asyncio
import pandas as pd
import os

from .point import Point

# constants
BASE_URL = 'https://www.mk8dx-lounge.com/api'
INITIAL_DETAILS = {'recruit': {},'channel_id': None}
INITIAL_RESULTS = []

BOT_IDS = (
    1038322985146273853, #main
    813078218344759326 # sheat
)
MY_ID = 1038322985146273853
CONFIG = json.loads(os.environ['CONFIG'])
credential_key = json.loads(os.environ['CREDENTIAL_KEY'])
name_key = json.loads(os.environ['NAME_KEY'])

# setup Google Cloud Storage
cloud_credentials = service_account.Credentials.from_service_account_info(credential_key['cloud_credentials'])
storage_client = storage.Client(
    project = name_key['project_id'],
    credentials= cloud_credentials
)
bucket = storage_client.bucket(name_key['bucket_name'])

# setup Google Spreadsheet
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
sheet_credentials = ServiceAccountCredentials.from_json_keyfile_dict(credential_key['sheet_credentials'], scope)
gc = gspread.authorize(sheet_credentials)
sh = gc.open('Analyzer-bot')



async def get(path: str, params: dict = {}) -> Optional[dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url = BASE_URL + path, params = params) as response:
            if response.status != 200:
                return None
            return await response.json()


async def get_lounger(
    player_id: Optional[int] = None,
    name: Optional[str] = None,
    mkc_id: Optional[int] = None,
    discord_id: Optional[int] = None,
    fc: Optional[str] = None,
    season: Optional[int] = None
) -> Optional[dict]:
    params = {}
    if player_id is not None:
        params['id'] = player_id
    elif name is not None:
        params['name'] = name
    elif mkc_id is not None:
        params['mkcId'] = mkc_id
    elif discord_id is not None:
        params['discordId'] = discord_id
    elif fc is not None:
        params['fc'] = fc
    else:
        return None
    if season is not None:
        params['season'] = season
    return await get(path='/player', params=params)


async def get_player_info(
    player_id: Optional[int] = None,
    name: Optional[str] = None,
    season: Optional[int] = None,
) -> Optional[dict]:
    params = {}
    if player_id is not None:
        params['id'] = player_id
    elif name is not None:
        params['name'] = name
    else:
        return None
    if season is not None:
        params['season'] = season
    return await get(path='/player/details',params=params)


def get_data(path: str) -> dict:
    blob = bucket.blob(path)
    return json.loads(blob.download_as_string())


def post_data(path: str, params: dict) -> None:
    blob = bucket.blob(path)
    blob.upload_from_string(
        data=json.dumps(params),
        content_type='application/json'
    )
    return


def get_guild_info(guild_id: int) -> dict:
    path = f'{guild_id}/details.json'
    try:
        return get_data(path)
    except NotFound:
        post_data(path, INITIAL_DETAILS)
        return INITIAL_DETAILS.copy()


def post_guild_info(guild_id: int, params: dict) -> None:
    post_data(f'{guild_id}/details.json',params)
    return


def get_results(guild_id: int) -> list[dict]:

    path = f'{guild_id}/results.json'
    try:
        return get_data(path)
    except NotFound:
        post_data(path,INITIAL_RESULTS)
        return INITIAL_RESULTS.copy()


def post_results(guild_id: int, point: Point, enemy: str, dt: datetime) -> None:
    result = get_results(guild_id)
    result.append({
        'score': point.ally,
        'enemyScore': point.enemy,
        'enemy': enemy,
        'date': dt.astimezone(tz=ZoneInfo(key='Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S')
    })
    df = pd.DataFrame(result)
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True)
    df.sort_values(by='date', ascending=True, inplace=True)
    df = df.copy()
    df['date'] = df['date'].astype(str)
    params = df.drop_duplicates().to_dict('records')
    post_data(path = f'{guild_id}/results.json', params=params)
    return


def get_sheet(sheet_name: str) -> dict:
    ret = {}
    worksheet = sh.worksheet(sheet_name)
    user_list=worksheet.get_all_records()
    for user in user_list:
        id = user.get('user_id')
        if id is not None:
            if str(id) != '':
                user.pop('user_id')
                ret[str(id)] = user
    return ret



def overwrite_sheet(sheet_name: str, values:list[list])->None:
    worksheet = sh.worksheet(sheet_name)
    worksheet.clear()
    sh.values_append(
        sheet_name,
        {'valueInputOption':'USER_ENTERED'},
        {'values':values}
    )
    return


def get_team_name(guild_id: int) -> Optional[str]:
    worksheet = sh.worksheet('team')
    guild_list = worksheet.get_all_values()
    for record in guild_list:
        if str(guild_id) == str(record[0]):
            if len(record) ==1:
                continue
            if record[1] is not None:
                if str(record[1]) != '':
                    return str(record[1])
    return


def set_team_name(
    guild_id: int,
    team_name: str
) -> None:
    is_existing = False
    worksheet = sh.worksheet('team')
    guild_list = worksheet.get_all_values()
    for record in guild_list:
        if len(record) ==1:
            continue
        if str(guild_id) == str(record[0]):
            record[1] = str(team_name)
            is_existing = True
            break
    if not is_existing:
        guild_list.append([str(guild_id),str(team_name)])
    overwrite_sheet('team',guild_list)
    return


def get_linked_id(discord_id: int, fill_blank: bool = False) -> Optional[int]:
    if discord_id is None:
        return None
    data_dict = get_sheet('link_account')
    user = data_dict.get(str(discord_id))
    if user is not None:
        if user['lounge_disco'] != '':
            return int(user['lounge_disco'])
    if fill_blank:
        return discord_id
    return


def get_linked_ids(discord_ids: list[int]) -> list[int]:
    data_dict = get_sheet('link_account')
    ret = []
    for discord_id in discord_ids:
        if discord_id is None:
            ret.append(None)
            continue
        user = data_dict.get(str(discord_id))
        if user is not None:
            ret.append(int(user['lounge_disco']))
        else:
            ret.append(discord_id)
    return ret


def set_lounge_id(
    discord_id: int,
    lounge_id: int
) -> None:
    data_dict = get_sheet('link_account')
    data_dict[str(discord_id)] = {'lounge_disco':str(lounge_id)}
    ids = list(data_dict.keys())
    user_ids = [str(id) for id in ids if str(id) !='']
    input_data  =[['user_id','lounge_disco']]
    for user_id in user_ids:
        input_data.append(
            [str(user_id),str(data_dict[user_id]['lounge_disco'])]
        )
    overwrite_sheet('link_account',input_data)
    return


async def get_player(
    name: Optional[str] = None,
    player_id: Optional[int] = None,
    discord_id: Optional[int] =None,
    mkc_id: Optional[int] = None,
    fc: Optional[str] = None,
    season: Optional[int] = None,
    search_linked_id: bool = True
)->Optional[dict]:
    if search_linked_id:
        discord_id = get_linked_id(discord_id,True)
    return await get_lounger(
        player_id = player_id,
        name = name,
        mkc_id = mkc_id,
        discord_id = discord_id,
        fc = fc,
        season = season
    )


async def get_players(
    discord_ids: list[int],
    season: Optional[int] = None,
    search_linked_id: bool = True,
    remove_None: bool = False,
    return_exceptions: bool = True
    ) -> list[Optional[dict]]:
    if search_linked_id:
        discord_ids = get_linked_ids(discord_ids)

    tasks = [asyncio.create_task(get_lounger(
        discord_id = discord_id,
        season = season
    ))for discord_id in discord_ids]
    players = await asyncio.gather(
        *tasks,
        return_exceptions = return_exceptions
    )

    if remove_None:
        return [player for player in players if player is not None]

    return players


RANK_DATA = {
            "Grandmaster": {
                "color": 0xA3022C,
                "url": "https://i.imgur.com/EWXzu2U.png"},
            "Master": {
                "color": 0xD9E1F2,
                "url": "https://i.imgur.com/3yBab63.png"},
            "Diamond": {
                "color": 0xBDD7EE,
                "url": "https://i.imgur.com/RDlvdvA.png"},
            "Ruby":{
                "color":0xD51C5E,
                "url": "https://i.imgur.com/WU2NlJQ.png"},
            "Sapphire": {
                "color": 0x286CD3,
                "url": "https://i.imgur.com/bXEfUSV.png"},
            "Platinum": {
                "color": 0x3FABB8,
                "url": "https://i.imgur.com/8v8IjHE.png"},
            "Gold": {
                "color": 0xFFD966,
                "url": "https://i.imgur.com/6yAatOq.png"},
            "Silver": {
                "color": 0xD9D9D9,
                "url": "https://i.imgur.com/xgFyiYa.png"},
            "Bronze": {
                "color": 0xC65911,
                "url": "https://i.imgur.com/DxFLvtO.png"},
            "Iron": {
                "color": 0x817876,
                "url": "https://i.imgur.com/AYRMVEu.png"},
        }



def get_rank(mmr: Union[int, float]) -> str:
    """season 8"""

    if mmr >= 17000:
        return "Grandmaster"
    elif mmr >= 16000:
        return "Master"
    elif mmr >= 15000:
        return "Diamond 2"
    elif mmr >= 14000:
        return "Diamond 1"
    elif mmr >= 13000:
        return "Ruby 2"
    elif mmr >= 12000:
        return "Ruby 1"
    elif mmr >= 11000:
        return "Sapphire 2"
    elif mmr >= 10000:
        return "Sapphire 1"
    elif mmr >= 9000:
        return "Platinum 2"
    elif mmr >= 8000:
        return "Platinum 1"
    elif mmr >= 7000:
        return "Gold 2"
    elif mmr >= 6000:
        return "Gold 1"
    elif mmr >= 5000:
        return "Silver 2"
    elif mmr >= 4000:
        return "Silver 1"
    elif mmr >= 3000:
        return "Bronze 2"
    elif mmr >= 2000:
        return "Bronze 1"
    elif mmr >= 1000:
        return "Iron 2"
    else:
        return "Iron 1"
