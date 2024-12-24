from datetime import date, timedelta, time
from typing import Any, Literal, Optional, overload

from aiosqlite import connect
from ujson import loads, dumps

from config import start_of_year, holidays

__all__ = (
    'init_all',
    'create_member',
    'create_class',
    'create_group',
    'create_bell',
    'create_subject',
    'create_hw',
    'get_members',
    'get_class',
    'get_group',
    'get_groups_by_ids',
    'get_bells',
    'get_subjects',
    'get_hw',
    'edit_member',
    'edit_class',
    'edit_group',
    'edit_subject',
    'edit_hw',
    'delete_group',
    'delete_bells_schedule',
    'delete_subject',
    'assign_to_group',
    'unassign_to_group',
    'hw_mark_completed',
    'get_bells_schedule',
    'get_schedule_for_day',
    'get_hw_for_day',
    'full_reset'
)

# Basic functions
path = 'data.db'


def format_values(values: dict[str, Any]) -> dict[str, Any]:
    return {k: repr(v) for k, v in values.items() if v is not None}


def __dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


async def create_table_ine(name: str, *columns: str):
    async with connect(path) as conn:
        await conn.execute(f'CREATE TABLE IF NOT EXISTS {name} ({','.join(columns)})')
        await conn.commit()


async def insert_into(table_name: str, **values: Any):
    async with connect(path) as conn:
        values = format_values(values)
        print(sql := f'INSERT INTO {table_name} ({','.join(values.keys())}) VALUES ({','.join(values.values())})')
        await conn.execute(sql)
        await conn.commit()
    return values


def where(**data: Any) -> str:
    data = format_values(data)
    return f'WHERE {' AND '.join([f'{k}={v}' for k, v in data.items()])}' if data else ''


def values(**data: Any) -> str:
    data = format_values(data)
    return ','.join([f'{k}={v}' for k, v in data.items()])


@overload
async def update(table_name: str, values: str, *additional: str): ...


async def update(table_name: str, *additional: str):
    async with connect(path) as conn:
        print(sql := f'UPDATE {table_name} SET {' '.join(additional)}')
        await conn.execute(sql)
        await conn.commit()


async def get_all_by(table_name: str, *additional: str) -> list[dict[str, Any]] | None:
    async with connect(path) as conn:
        conn.row_factory = __dict_factory
        print(sql := f'SELECT * FROM {table_name} {' '.join(additional)}')
        async with conn.execute(sql) as cur:
            r = await cur.fetchall()
    return r


async def get_one_by(table_name: str, *additional: str) -> dict[str, Any] | None:
    res = await get_all_by(table_name, *additional)
    return res[0] if res else None


async def delete_from(table_name: str, *additional: str) -> list[dict[str, Any]] | None:
    async with connect(path) as conn:
        to_delete = await get_all_by(table_name, *additional)
        print(sql := f'DELETE FROM {table_name} {' '.join(additional)}')
        await conn.execute(sql)
        await conn.commit()
    return to_delete


async def get_next_id(table_name: str, *additional: str):
    async with connect(path) as conn:
        conn.row_factory = __dict_factory
        print(sql := f'SELECT MAX(id) FROM {table_name} {' '.join(additional)}')
        async with conn.execute(sql) as cur:
            r = await cur.fetchone()
    return int(x) + 1 if r and (x := r.get('MAX(id)')) else 1


#

# Init tables
async def init_members():
    await create_table_ine(
        'members',
        'id int',
        'class_id int',
        'name text',
        'groups_ids text'
    )


async def init_classes():
    await create_table_ine(
        'classes',
        'id int',
        'name text',
        'ggid int',
        'groups_ids text'
    )


async def init_groups():
    await create_table_ine(
        'groups',
        'id int',
        'name text'
    )


async def init_bells():
    await create_table_ine(
        'bells',
        'class_id int',
        'type int', # 0 - food, 1-9 - number of lesson
        'name text',
        'start_time text', # ex. [8, 0] - 8:00
        'end_time text' # same
    )


async def init_subjects():
    await create_table_ine(
        'subjects',
        'id int',
        'class_id int',
        'groups_ids text',
        'name text',
        'schedule text',
        # How schedule works?
        # it's text with two letters
        # (first - day (from 0 to 9, 0, 1, 2, 3, 4 - from monday to friday at odd week (1, 3, ...)
        # 5, 6, 7, 8, 9 - from monday to friday at even week (2, 4, ...)
        # second - lesson index (1, 2, 3, 4, 5, 6, 7, 8))
        # example: 01025152 compiles how 'at monday at 1st and 2nd class'
        'office text',
        'teacher text'
    )


async def init_hw():
    await create_table_ine(
        'hw',
        'id int',
        'subject_id int',
        'text text',
        'date text', # ex. 1511 - 15 november
        'files text', # ex. [b'hello, world', b'hi!']
        'completed text' # ex. [14874383, 3537396] ids of users, which completed this hw
    )


async def init_all():
    await init_members()
    await init_classes()
    await init_groups()
    await init_bells()
    await init_subjects()
    await init_hw()
#

# Create
async def create_member(user_id: int, class_id: int, name: str, groups_ids: Optional[list[int]] = None):
    if groups_ids is None:
        groups_ids = []
    return await insert_into(
        'members',
        id=user_id,
        class_id=class_id,
        name=name,
        groups_ids=dumps(groups_ids)
    )


async def create_class(name: str):
    class_id = await get_next_id('classes')

    gg = await create_group(class_id)
    ggid = gg['id']

    return await insert_into(
        'classes',
        id=class_id,
        name=name,
        ggid=ggid,
        groups_ids='[]'
    )


async def create_group(class_id: int, name: str = ''):
    group_id = await get_next_id('groups')

    if name:
        groups_ids = (await get_class(class_id))['groups_ids']
        await edit_class(class_id, groups_ids=groups_ids + [group_id])
    return await insert_into(
        'groups',
        id=group_id,
        name=name
    )


async def create_bell(class_id: int, type: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], name: Optional[str] = None,
                      start_time: tuple[int, int] = None, end_time: tuple[int, int] = None):
    return await insert_into(
        'bells',
        class_id=class_id,
        type=type,
        name=name,
        start_time=dumps(list(start_time)),
        end_time=dumps(list(end_time))
    )


async def create_subject(class_id: int, groups_ids: list[int], name: str, schedule: str, office: Optional[str] = None,
                         teacher: Optional[str] = None):
    subject_id = await get_next_id('subjects')
    return await insert_into(
        'subjects',
        id=subject_id,
        class_id=class_id,
        groups_ids=dumps(groups_ids),
        name=name,
        schedule=schedule,
        office=office,
        teacher=teacher
    )


async def create_hw(subject_id: int, text: Optional[str] = None, d: date = None, files: list[str] = []):
    hw_id = await get_next_id('hw')
    return await insert_into(
        'hw',
        id=hw_id,
        subject_id=subject_id,
        text=text,
        date=d.strftime('%d%m') if d else None,
        files=dumps(files),
        completed='[]'
    )
#

# Get
async def get_members(user_id: Optional[int] = None, class_id: Optional[int] = None, name: Optional[str] = None,
                      groups_ids: Optional[list[int]] = None):
    m = await get_all_by('members', where(
        id=user_id,
        class_id=class_id,
        name=name,
        groups_ids=dumps(groups_ids) if groups_ids is not None else None
    ))
    for i in m:
        i['groups_ids'] = loads(i['groups_ids'])
    return m


async def get_class(class_id: Optional[int] = None, name: Optional[str] = None, ggid: Optional[int] = None,
                    groups_ids: Optional[list[int]] = None):
    c = await get_one_by('classes', where(
        id=class_id,
        name=name,
        ggid=ggid,
        groups_ids=dumps(groups_ids) if groups_ids is not None else None
    ))
    c['groups_ids'] = loads(c['groups_ids'])
    return c


async def get_group(group_id: Optional[int] = None, name: Optional[str] = None):
    return await get_one_by('groups', where(
        id=group_id,
        name=name
    ))


async def get_groups_by_ids(groups_ids: list[int]):
    return [(await get_group(i)) for i in groups_ids]


async def get_bells(class_id: Optional[int] = None, type: Optional[int] = None, name: Optional[str] = None,
                    start_time: Optional[tuple[int, int]] = None, end_time: Optional[tuple[int, int]] = None):
    bells = await get_all_by('bells', where(
        class_id=class_id,
        type=type,
        name=name,
        start_time=start_time,
        end_time=end_time
    ))

    for i in bells:
        i['start_time'] = loads(i['start_time'])
        i['end_time'] = loads(i['end_time'])
    return bells


async def get_subjects(
        subject_id: Optional[int] = None,
        class_id: Optional[int] = None,
        groups_ids: Optional[list[int]] = None,
        name: Optional[str] = None,
        schedule: Optional[str] = None,
        office: Optional[str] = None,
        teacher: Optional[str] = None
):
    subj = await get_all_by('subjects', where(
        id=subject_id,
        class_id=class_id,
        groups_ids=dumps(groups_ids) if groups_ids else None,
        name=name,
        schedule=schedule,
        office=office,
        teacher=teacher
    ))
    if subj:
        for i in subj:
            i['groups_ids'] = loads(i['groups_ids'])
    return subj

async def get_hw(hw_id: Optional[int] = None, subject_id: Optional[int] = None, text: Optional[str] = None,
                 d: Optional[date] = None, files: Optional[list[str]] = None, completed: Optional[list[int]] = None):
    hw = await get_one_by(
        'hw', where(
        id=hw_id,
        subject_id=subject_id,
        text=text,
        date=d.strftime('%d%m') if d else None,
        files=dumps(files) if files else None,
        completed=dumps(completed) if completed else None
    ))
    if hw:
        hw['files'] = loads(hw['files'])
        hw['completed'] = loads(hw['completed'])
    return hw
#

# Edit
async def edit_member(user_id: int, name: Optional[str] = None, groups_ids: Optional[list[int]] = None):
    await update('members', values(
        name=name,
        groups_ids=dumps(groups_ids) if groups_ids is not None else None
    ), where(id=user_id))


async def edit_class(class_id: int, name: Optional[str] = None, groups_ids: Optional[list[int]] = None):
    await update('classes', values(
        name=name,
        groups_ids=dumps(groups_ids) if groups_ids is not None else None
    ), where(id=class_id))


async def edit_group(group_id: int, name: str):
    await update('groups', values(name=name), where(id=group_id))


async def edit_subject(
        subject_id: int,
        groups_ids: Optional[list[int]] = None,
        name: Optional[str] = None,
        schedule: Optional[str] = None,
        office: Optional[str] = None,
        teacher: Optional[str] = None
):
    await update('subjects', values(
        groups_ids=dumps(groups_ids) if groups_ids is not None else None,
        name=name,
        schedule=schedule,
        office=office,
        teacher=teacher
    ), where(id=subject_id))

async def edit_hw(hw_id: int, subject_id: Optional[int] = None, text: Optional[str] = None,
                  d: Optional[date] = None, files: Optional[list[str]] = None, completed: Optional[list[int]] = None):
    await update('hw', values(
        subject_id=subject_id,
        text=text,
        date=d.strftime('%d%m') if d else None,
        files=dumps(files) if files else None,
        completed=dumps(completed) if completed else None
    ), where(id=hw_id))
#

# Delete
async def delete_group(group_id: int, class_id: Optional[int] = None, name: Optional[str] = None):
    if class_id:  # Delete group usages in class
        cl_groups_ids: list[int] = (await get_class(class_id))['groups_ids']
        cl_groups_ids.remove(group_id)
        await edit_class(class_id, groups_ids=cl_groups_ids)

        for i in (await get_members(class_id=class_id)):
            await unassign_to_group(i['id'], group_id)
    return await delete_from('groups', where(
        id=group_id,
        name=name
    ))


async def delete_bells_schedule(class_id: int):
    return await delete_from('bells', where(class_id=class_id))


async def delete_subject(
        subject_id: Optional[int] = None,
        class_id: Optional[int] = None,
        groups_ids: Optional[list[int]] = None,
        name: Optional[str] = None,
        schedule: Optional[str] = None,
        office: Optional[str] = None,
        teacher: Optional[str] = None
):
    subj = await delete_from('subjects', where(
        id=subject_id,
        class_id=class_id,
        groups_ids=dumps(groups_ids) if groups_ids else None,
        name=name,
        schedule=schedule,
        office=office,
        teacher=teacher
    ))
    for i in subj:
        i['groups_ids'] = loads(i['groups_ids'])
    return subj
#

# Utils
async def assign_to_group(user_id: int, group_id: int):
    groups_ids = (await get_members(user_id))[0]['groups_ids']
    if group_id not in groups_ids:
        groups_ids.append(group_id)
    await edit_member(user_id, groups_ids=groups_ids)


async def unassign_to_group(user_id: int, group_id: int):
    groups_ids: list[int] = (await get_members(user_id))[0]['groups_ids']
    if group_id in groups_ids:
        groups_ids.remove(group_id)
    await edit_member(user_id, groups_ids=groups_ids)


async def hw_mark_completed(user_id: int, hw_id: int):
    hw = await get_hw(hw_id)
    if hw:
        completed = hw['completed']
        completed.append(user_id)
        await edit_hw(hw_id, completed=completed)


async def get_bells_schedule(class_id: int) -> list[tuple[time, time, int, str | None]]:
    ans = []
    bells = (await get_bells(class_id)) or []
    for i in bells:
        s = i['start_time']
        e = i['end_time']
        ans.append((time(s[0], s[1], 0), time(e[0], e[1], 0), i['type'], i.get('name')))
    return ans



async def get_schedule_for_day(class_id: int, groups_ids: list[int],
                               day: date) -> dict[int, dict[str, Any] | None]:
    # get (even or odd)? week
    d = day
    weeks = [start_of_year + timedelta(days=7 * i) for i in range((d - date(d.year, 9, 2)).days // 7 + 1)]
    for i in holidays:
        try:
            weeks.remove(i)
        except ValueError:
            pass
    is_even = len(weeks) % 2 == 0

    subjects = await get_subjects(class_id=class_id) or []

    result = {
        1: None,
        2: None,
        3: None,
        4: None,
        0: None,
        5: None,
        6: None,
        7: None,
        8: None,
        9: None
    }

    if day.weekday() not in [5, 6]: # If not weekend
        for subj in subjects:
            is_in_groups_ids = subj['groups_ids'] == []
            for i in groups_ids:
                if i in subj['groups_ids']:
                    is_in_groups_ids = True
            if is_in_groups_ids:
                sch: str = subj['schedule']
                for si in range(len(sch) // 2):
                    sday, slesson = int(sch[2 * si]), int(sch[2 * si + 1])
                    # 0, 1, 2, 3, 4 - odd
                    # 5, 6, 7, 8, 9 - even
                    if is_even:
                        sday -= 5
                    if sday == day.weekday():
                        result[slesson] = subj
    return result


async def get_hw_for_day(class_id: int, groups_ids: list[int],
                         day: date) -> dict[int, dict[str, Any] | None]:
    schedule = await get_schedule_for_day(class_id, groups_ids, day)
    del schedule[0]
    return {
        cn: (await get_hw(subject_id=subj['id'], d=day)) if subj else None
        for cn, subj in schedule.items()
    }


def full_reset():
    with open(path, 'w') as f: f.write('')
#
