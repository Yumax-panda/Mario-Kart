from __future__ import annotations
from typing import TYPE_CHECKING, Union, Optional, Any
from discord.ext import commands, pages
from io import BytesIO
import pandas as pd

from datetime import datetime
from zoneinfo import ZoneInfo

from .errors import *
from common import (
    Point,
    get_results,
    get_dt,
    get_integers,
    post_results,
    post_data
)

if TYPE_CHECKING:
    from discord import Attachment

def WinOrLose(diff: int) -> str:

    if diff < 0:
        return 'Lose'
    elif diff == 0:
        return 'Draw'
    return 'Win'


def get(guild_id: int) -> pd.DataFrame:
    results = get_results(guild_id)

    if results:
        df = pd.DataFrame(results)
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'], infer_datetime_format = True)
        return df.sort_values(
            by = 'date',
            ascending = True,
            inplace = False
        )

    raise EmptyResult


def post_df(guild_id, df: pd.DataFrame) -> None:
    df.sort_values(by = 'date', ascending = True, inplace = True)
    df = df.copy()
    df['date'] = df['date'].astype(str)
    post_data(
        path = f'{guild_id}/results.json',
        params = df.drop_duplicates().to_dict('records')
    )
    return


class ResultPaginator(pages.Paginator):

    def __init__(
        self,
        body: list[str],
        header: str,
        footer: str,
        top: str = ''
    ) -> None:
        result_page = commands.Paginator(prefix = '', max_size = 800)

        for content in body:
            result_page.add_line(content)

        is_compact: bool = len(result_page.pages) == 1
        super().__init__(
            pages = [top + '```' + header + b + footer for b in result_page.pages],
            show_indicator = not is_compact,
            show_disabled = not is_compact,
            author_check= False
        )
        self.current_page = self.page_count




def show_all(guild_id: int) -> ResultPaginator:
    df = get(guild_id)
    df['formatted_scores'] = df['score'].astype(str) + ' - ' + df['enemyScore'].astype(str)
    df['diff'] = df['score'] - df['enemyScore']
    lines = df.to_string(
        columns = ['formatted_scores', 'enemy', 'diff'],
        formatters = {'diff': WinOrLose},
        header = ['Scores', 'Enemy', 'Result'],
        justify = 'center'
    ).split('\n')
    win, lose, draw = len(df[df['diff']>0]), len(df[df['diff']<0]), len(df[df['diff']==0])
    return ResultPaginator(
        body = lines[1:],
        header = lines[0],
        footer = f'__**Win**__:  {win}  __**Lose**__:  {lose}  __**Draw**__:  {draw}  [{len(df)}]'
    )


def search_results(guild_id:int, name: str) -> Union[ResultPaginator, list[str]]:
    d = get(guild_id)
    df = d.query(f'enemy=="{name}"').copy()

    if len(df) == 0:
        name_list: list[str] = d['enemy'].unique().tolist()
        prefix = name[0].lower()
        return [n for n in name_list if n[0].lower() == prefix]

    df['formatted_scores'] = df['score'].astype(str) + ' - ' + df['enemyScore'].astype(str)
    df['diff'] = df['score'] - df['enemyScore']
    df['date']=df['date'].dt.strftime('%Y/%m/%d').copy()
    lines = df.to_string(
        columns = ['date', 'formatted_scores', 'diff'],
        formatters = {'diff': WinOrLose},
        header = ['Date', 'Scores', 'Result'],
        justify = 'center'
    ).split('\n')
    win, lose, draw = len(df[df['diff']>0]), len(df[df['diff']<0]), len(df[df['diff']==0])
    return ResultPaginator(
        top = f'vs **{name}**',
        body = lines[1:],
        header = lines[0],
        footer = f'__**Win**__:  {win}  __**Lose**__:  {lose}  __**Draw**__:  {draw}  [{len(df)}]'
    )


def register(
    guild_id: int,
    enemy: str,
    scores: str,
    date: str
) -> dict[str, str]:
    data = {'enemy': enemy}


    if date == '':
        data['dt'] = datetime.now(tz=ZoneInfo(key='Asia/Tokyo'))
    else:
        data['dt'] = get_dt(date)

    numbers = get_integers(scores)

    if len(numbers) == 1:
        data['point'] = Point(numbers[0], 984-numbers[0])
    elif len(numbers) == 2:
        data['point'] = Point(numbers[0], numbers[1])
    else:
        raise InvalidScoreInput

    post_results(guild_id, **data)
    return data


def delete(guild_id: int, ids: str, locale: str = 'ja') -> ResultPaginator:
    df = get(guild_id)
    ids: list[int] = sorted(get_integers(ids))

    if not ids:
        raise InvalidIdInput

    try:
        dropped = df.iloc[ids].copy()
    except IndexError:
        raise IdOutOfRange

    dropped['formatted_scores'] = dropped['score'].astype(str) + ' - ' + dropped['enemyScore'].astype(str)
    dropped['date'] = dropped['date'].dt.strftime('%Y/%m/%d').copy()
    df.drop(
        index = df.index[ids],
        errors = 'raise',
        inplace = True
    )

    post_df(guild_id, df)
    lines = dropped.to_string(
        columns = ['enemy', 'formatted_scores', 'date'],
        header = ['Enemy', 'Scores', 'Date'],
        justify = 'center'
    ).split('\n')
    return ResultPaginator(
        body = lines[1:],
        header = lines[0],
        footer = '',
        top = {'ja': '戦績を削除しました。'}.get(locale, 'Successfully deleted.')
    )


def edit(
    guild_id: int,
    result_id: int,
    enemy: Optional[str] = None,
    scores: Optional[str] = None,
    date: Optional[str] = None,
) -> dict[str, Any]:
    df = get(guild_id)

    try:
        data = {
            'score': df.at[result_id, 'score'],
            'enemyScore': df.at[result_id, 'enemyScore'],
            'enemy': enemy or df.at[result_id, 'enemy'],
            'date': df.at[result_id, 'date'],
        }
    except KeyError:
        raise IdOutOfRange

    if scores is not None:
        numbers = get_integers(scores)

        if not 1<= len(numbers) <=2:
            raise InvalidScoreInput

        if len(numbers) >= 1:
            data['score'] = numbers[0]
        if len(numbers) == 2:
            data['enemyScore'] = numbers[1]

    if date is not None:
        data['date'] = get_dt(date).replace(tzinfo=None)

    df.loc[result_id] = data
    post_df(guild_id, df)
    return {'enemy': data['enemy'], 'point': Point(data['score'], data['enemyScore']), 'dt': data['date']}


def export_file(guild_id: int, name: str) -> BytesIO:
    data = get_results(guild_id)

    if not data:
        raise EmptyResult

    df = pd.DataFrame(data)
    df.insert(0, 'team', name)
    buffer = BytesIO()
    df.to_csv(
        buffer,
        encoding = 'utf-8',
        header = False,
        index = False,
        columns = ['team','score','enemyScore','enemy','date']
    )
    buffer.seek(0)
    return buffer


async def load_file(guild_id: int, file: Attachment) -> None:
    buffer = BytesIO()
    await file.save(buffer)

    try:
        df = pd.read_csv(
            buffer,
            skipinitialspace = True,
            header = None
        ).loc[:,[1,2,3,4]]
        df.columns = ['score','enemyScore','enemy','date']
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'], infer_datetime_format = True)
        df.sort_values(by = 'date', ascending = True, inplace = False)
        post_df(guild_id, df)
    except Exception:
        raise NotAcceptableContent
