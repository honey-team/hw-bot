from optparse import Option
from tokenize import group
from typing import Any, Optional, overload
from aiosqlite import connect
from ujson import loads, dumps


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
    return f'WHERE {' AND '.join([f'{k}={v}' for k, v in data.items() if v is not None])}' if data else ''

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

async def get_max(table_name: str, column_name: str, *additional: str):
    async with connect(path) as conn:
        conn.row_factory = __dict_factory
        print(sql := f'SELECT MAX({column_name}) FROM {table_name} {' '.join(additional)}')
        async with conn.execute(sql) as cur:
            r = await cur.fetchone()
    return r
        
async def init_members():
    await create_table_ine(
        'members',
        'user_id long',
        'name text',
        'class_id int',
        'groups_ids text'
    )


async def create_member(id: int, class_id: int, name: str, group_id: Optional[int] = None):
    if not group_id: group_id = (await get_general_group(class_id))['group_id']
    return await insert_into(
        'members',
        user_id=id,
        name=name,
        class_id=class_id,
        groups_ids=f'[{group_id}]'
    )


async def assign_to_group(user_id: int, group_id: int):
    mb = await get_member(user_id)
    await update('members', values(
        groups_ids=dumps(loads(mb['groups_ids']) + [group_id])
    ))
    
async def unassign_to_group(user_id: int, group_id: int):
    mb = await get_member(user_id)
    await update('members', values(
        groups_ids=dumps(loads(mb['groups_ids']) - [group_id])
    ))

async def get_all_members(id: Optional[int] = None, class_id: Optional[int] = None, group_id: Optional[int] = None):
    return await get_all_by('members', where(
        user_id=id,
        class_id=class_id,
        group_id=group_id
    ))
    

async def get_member(id: int, class_id: Optional[int] = None, group_id: Optional[int] = None) -> dict[str, int]:
    return await get_one_by('members', where(
        user_id=id,
        class_id=class_id,
        group_id=group_id
    ))

async def delete_members(id: Optional[int] = None, class_id: Optional[int] = None, group_id: Optional[int] = None) -> list[dict[str, int]]:
    return await delete_from('members', where(
        user_id=id,
        class_id=class_id,
        group_id=group_id
    ))

async def init_classes():
    await create_table_ine(
        'classes',
        'class_id int',
        'name text'
    )

async def create_class(name: str, user_id: int, member_name: str):
    try:
        _max_i = int(await get_max('classes', 'class_id').get('class_id', 0))
    except:
        _max_i = 0
    cl = await insert_into(
        'classes',
        class_id=_max_i + 1,
        name=name
    )
    await create_general_group(cl['class_id'], user_id, member_name)
    return cl

async def get_class(class_id: int, name: Optional[str] = None):
    return await get_one_by('classes', where(
        class_id=class_id,
        name=name
    ))
    
async def init_subjects():
    await create_table_ine(
        'subjects',
        'class_id int',
        'groups_ids text',
        'name text',
        'schedule text' # 1112 means 1 - monday; 1, 2 classes, 9 - one by two weeks at thursday (2)
    )

async def init_groups():
    await create_table_ine(
        'groups',
        'class_id int',
        'group_id int',
        'name text',
        'general bool'
    )

async def create_group(class_id: int, name: str, user_id: int, general: bool = False):
    class_id = int(class_id)
    try:
        _max_i = int(await get_max('groups', 'group_id').get('group_id', 0))
    except:
        _max_i = 0
    gr = await insert_into(
        'groups',
        class_id=class_id,
        group_id=_max_i + 1,
        name=name,
        general=general
    )
    await assign_to_group(user_id, gr['group_id'])
    return gr

async def create_general_group(class_id: int, user_id: int, member_name: str):
    try:
        _max_i = int(await get_max('groups', 'group_id').get('group_id', 0))
    except:
        _max_i = 0
    await create_member(user_id, class_id, member_name, _max_i + 1)
    return await create_group(class_id, '', user_id, True)


async def get_all_groups(class_id: int, group_id: Optional[int] = None, name: Optional[str] = None, general: Optional[bool] = None) -> dict[str, str | int]:
    return await get_all_by('groups', where(
        class_id=class_id,
        group_id=group_id,
        name=name,
        general=general
    ))

async def get_group(class_id: int, group_id: Optional[int] = None, name: Optional[str] = None) -> dict[str, int | str]:
    return await get_one_by('groups', where(
        class_id=class_id,
        group_id=group_id,
        name=name
    ))

async def get_general_group(class_id: int):
    return await get_one_by('groups', where(
        class_id=class_id,
        general=True
    ))

async def delete_group(class_id: Optional[int] = None, group_id: Optional[int] = None, name: Optional[str] = None) -> dict[str, int | str]:
    if group_id:
        await delete_members(group_id=group_id)
    
    return await delete_from('groups', where(
        class_id=class_id,
        group_id=group_id,
        name=name
    ))

async def init_hw():
    await create_table_ine(
        'hw',
        'class_id int',
        'group_id int',
        'text text',
        'files text'
    )

async def init_all():
    await init_members()
    await init_classes()
    await init_subjects()
    await init_groups()
    await init_hw()

def get_groups_from_dict(member: dict[str, Any]):
    return loads(member['groups_ids'])

def full_reset():
    with open(path, 'w') as f:
        f.write("")
