from common import sqlBase


def getConfigValue(key, default=None):
    rst = sqlBase.fetchall_to_table("select value from system_config where key=?", (key,))
    if rst:
        return rst[0]['value']
    return default


def setConfigValue(key, value):
    sqlBase.execute_update(
        "insert into system_config(key, value, updateTime) values (?, ?, strftime('%s', 'now')) "
        "on conflict(key) do update set value=excluded.value, updateTime=strftime('%s', 'now')",
        (key, value)
    )
