from typing import Any, Optional, overload
from aiosqlite import connect
from ujson import loads, dumps

__all__ = (
    'init_all',
    'create_member',
    'create_class',
    'create_group',
    'get_members',
    'get_class',
    'get_group',
    'get_groups_by_ids',
    'edit_member',
    'edit_class',
    'edit_group',
    'delete_group',
    'assign_to_group',
    'unassign_to_group',
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

async def init_all():
    await init_members()
    await init_classes()
    await init_groups()
#

# Create
async def create_member(user_id: int, class_id: int, name: str, groups_ids: list[int] = []):
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
#

# Get
async def get_members(user_id: Optional[int] = None, class_id: Optional[int] = None, name: Optional[str] = None, groups_ids: Optional[list[int]] = None):
    m = await get_all_by('members', where(
        id=user_id,
        class_id=class_id,
        name=name,
        groups_ids=dumps(groups_ids) if groups_ids is not None else None
    ))
    for i in m:
        i['groups_ids'] = loads(i['groups_ids'])
    return m

async def get_class(class_id: Optional[int] = None, name: Optional[str] = None, ggid: Optional[int] = None, groups_ids: Optional[list[int]] = None):
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
#

# Edit
async def edit_member(user_id: int, name: Optional[str] = None, groups_ids: Optional[list[int]] = None):
    await update('members', values(
            name=name,
            groups_ids=dumps(groups_ids) if groups_ids is not None else None
        ),
        where(id=user_id)
    )

async def edit_class(class_id: int, name: Optional[str] = None, groups_ids: Optional[list[int]] = None):
    await update('classes', values(
            name=name,
            groups_ids=dumps(groups_ids) if groups_ids is not None else None
        ),
        where(id=class_id)
    )

async def edit_group(group_id: int, name: str):
    await update('groups', values(name=name), where(id=group_id))
#

# Delete
async def delete_group(group_id: Optional[int] = None, name: Optional[str] = None):
    return await delete_from('groups', where(
            group_id=group_id,
            name=name
        )
    )
#

# Utils
async def assign_to_group(user_id: int, group_id: int):
    old_groups_ids = (await get_members(user_id))[0]['groups_ids']
    new_groups_ids = old_groups_ids + [group_id]
    await edit_member(user_id, groups_ids=new_groups_ids)

async def unassign_to_group(user_id: int, group_id: int):
    groups_ids: list[int] = (await get_members(user_id))[0]['groups_ids']
    if group_id in groups_ids:
        groups_ids.remove(group_id)
    await edit_member(user_id, groups_ids=groups_ids)

def full_reset():
    with open(path, 'w') as f: f.write('') 
#
