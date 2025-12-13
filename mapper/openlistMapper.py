"""
@Author：dr34m
@Date  ：2024/7/8 16:52 
"""
from common import sqlBase
from common.LNG import G


def getOpenlistList():
    return sqlBase.fetchall_to_table("select * from list")


def getOpenlistById(openlistId):
    rst = sqlBase.fetchall_to_table("select * from list where id=?", (openlistId,))
    if rst:
        return rst[0]
    else:
        raise Exception(G('alist_not_found'))


def addOpenlist(openlist):
    return sqlBase.execute_insert("insert into list (remark, url, userName, token) "
                                  "values (:remark, :url, :userName, :token)", openlist)


def updateOpenlist(openlist):
    sqlBase.execute_update(f"update list set remark=:remark, url=:url"
                           f"{', token=:token' if 'token' in openlist else ''}"
                           f" where id=:id", openlist)


def removeOpenlist(openlistId):
    sqlBase.execute_update("delete from list where id=?", (openlistId,))
