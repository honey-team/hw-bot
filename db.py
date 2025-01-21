import logging
from datetime import date, datetime, timedelta, time
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
    'delete_subjects',
    'assign_to_group',
    'unassign_to_group',
    'hw_mark_completed',
    'hw_mark_uncompleted',
    'get_bells_schedule',
    'get_schedule_for_day',
    'get_hw_for_day',
    'get_conf',
    'set_conf',
    'full_reset'
)

from logger import logger

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

        logging.log(logging.INFO,
                   sql := f'INSERT INTO {table_name} ({','.join(values.keys())}) VALUES ({','.join(values.values())})')
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
        logging.log(logging.INFO, sql := f'UPDATE {table_name} SET {' '.join(additional)}')
        await conn.execute(sql)
        await conn.commit()


async def get_all_by(table_name: str, *additional: str) -> list[dict[str, Any]] | None:
    async with connect(path) as conn:
        conn.row_factory = __dict_factory
        logging.log(logging.INFO, sql := f'SELECT * FROM {table_name} {' '.join(additional)}')
        async with conn.execute(sql) as cur:
            r = await cur.fetchall()
    return r


async def get_one_by(table_name: str, *additional: str) -> dict[str, Any] | None:
    res = await get_all_by(table_name, *additional)
    return res[0] if res else None


async def delete_from(table_name: str, *additional: str) -> list[dict[str, Any]] | None:
    async with connect(path) as conn:
        to_delete = await get_all_by(table_name, *additional)
        logging.log(logging.INFO, sql := f'DELETE FROM {table_name} {' '.join(additional)}')
        await conn.execute(sql)
        await conn.commit()
    return to_delete


async def get_next_id(table_name: str, *additional: str):
    async with connect(path) as conn:
        conn.row_factory = __dict_factory
        logging.log(logging.INFO, sql := f'SELECT MAX(id) FROM {table_name} {' '.join(additional)}')
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
                      start_time: tuple[int, int] | list[int] = None, end_time: tuple[int, int] | list[int] = None):
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
        files=dumps(files) if files is not None else None,
        completed=dumps(completed) if completed is not None else None
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


async def delete_subjects(
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
        await edit_hw(hw_id, completed=list(set(hw['completed'] + [user_id])))


async def hw_mark_uncompleted(user_id: int, hw_id: int):
    hw = await get_hw(hw_id)
    if hw:
        completed = hw['completed']
        if user_id in completed:
            completed.remove(user_id)
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
    

async def get_lesson_or_break(
    dt: datetime,
    class_id: int,
    groups_ids: list[int]
) -> tuple[bool, time, time, dict[str, Any] | None, timedelta] | None: # is_break, start_time, end_time, subject, to_end
    schedule = await get_schedule_for_day(class_id, groups_ids, dt.date())
    bells = await get_bells_schedule(class_id)
    
    subj = {}
    
    def __get_diff(t1: time, t2: time) -> timedelta:
        dt1 = datetime(dt.year, dt.month, dt.day, t1.hour, t1.minute, t1.second, t1.microsecond)
        dt2 = datetime(dt.year, dt.month, dt.day, t2.hour, t2.minute, t2.second, t2.microsecond)
        return dt1 - dt2
    
    if bells:
        current_bell = -1, -1
        for bell in bells:
            if bell[0] < dt.time() < bell[1]:
                current_bell = bell[0], bell[1]
                subj['type'] = bell[2]
                if bell[2] == 0:
                    subj['name'] = bell[3]
                else:
                    subj = schedule[bell[2]]
        
        if current_bell[0] == -1 and current_bell[1] == -1:
            for i, bell in enumerate(bells):
                if i < len(bells) - 1:
                    nextbell = bells[i+1]
                    if bell[1] < dt.time() < nextbell[0]:
                        return (True, bell[1], nextbell[0], schedule[nextbell[2]] if i < len(bells)-1 else None,
                                __get_diff(nextbell[0], dt.time()))
        else:
            return False, current_bell[0], current_bell[1], subj, __get_diff(current_bell[1], dt.time())
    else:
        return None


async def get_conf(class_id: int) -> dict[str, Any]:
    result = {
        'members': [],
        'groups': [],
        'subjects': [],
        'bells': []
    }
    class_ = await get_class(class_id)

    async def __get_group_names(__groups_ids: list[int]) -> list[str]:
        groups_names = []
        for group_id in __groups_ids:
            groups_names.append((await get_group(group_id))['name'])
        return groups_names

    #
    for member in await get_members(class_id=class_id):
        result['members'].append({
            'id': member['id'],
            'name': member['name'],
            'groups': await __get_group_names(member['groups_ids'])
        })

    for group_name in await __get_group_names(class_['groups_ids']):
        result['groups'].append({'name': group_name})

    for subject in await get_subjects(class_id=class_id):
        result['subjects'].append({
            'groups': await __get_group_names(subject['groups_ids']),
            'name': subject['name'],
            'schedule': subject['schedule'],
            'office': subject['office'],
            'teacher': subject['teacher']
        })

    for bell_start_time, bell_end_time, bell_type, bell_name in await get_bells_schedule(class_id):
        result['bells'].append({
            'lesson': bell_type,
            'name': bell_name,
            'start_time': bell_start_time.strftime('%H:%M'),
            'end_time': bell_start_time.strftime('%H:%M')
        })

    return result

async def set_conf(class_id: int, data: dict[str, Any]) -> None:
    async def __get_group_ids(__groups_names: list[str]) -> list[int]:
        groups_ids = []
        for group_name in __groups_names:
            groups_ids.append((await get_group(name=group_name))['id'])
        return groups_ids

    # Create groups (if not exists)
    for group in data['groups']:
        if not await get_group(name=group['name']):
            await create_group(class_id, group['name'])

    # Add members (if not exists)
    for member in data['members']:
        if not await get_members(member['id']):
            await create_member(member['id'], class_id, member['name'], await __get_group_ids(member['groups']))

    # Reset subjects
    await delete_subjects(class_id=class_id)
    # Create subjects
    for subject in data['subjects']:
        if not await get_subjects(name=subject['name']):
            await create_subject(
                class_id,
                await __get_group_ids(subject['groups']),
                subject['name'],
                subject['schedule'],
                subject['office'],
                subject['teacher']
            )

    # Reset bells
    await delete_bells_schedule(class_id)
    # Create bells
    for bell in data['bells']:
        await create_bell(class_id, bell['lesson'], bell['name'],
                          [int(i) for i in bell['start_time'].split(':')],
                          [int(i) for i in bell['end_time'].split(':')])


def full_reset():
    with open(path, 'w') as f: f.write('')
#
