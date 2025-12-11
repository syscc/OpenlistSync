import logging

from common.LNG import G
from mapper.alistMapper import getAlistById, addAlist, removeAlist, getAlistList, updateAlist
from service.openlist.openlistClient import OpenListClient

openlistClientList = {}


def getClientList():
    clientList = getAlistList()
    for client in clientList:
        del client['token']
    return clientList


def getClientById(openlistId):
    global openlistClientList
    if openlistId not in openlistClientList:
        ol = getAlistById(openlistId)
        openlistClientList[openlistId] = OpenListClient(ol['url'], ol['token'], openlistId)
    return openlistClientList[openlistId]


def updateClient(openlist):
    openlistId = openlist['id']
    if openlist['remark'] is not None and openlist['remark'].strip() == '':
        openlist['remark'] = None
    if 'token' in openlist:
        if openlist['token'] is None:
            del openlist['token']
        else:
            openlist['token'] = openlist['token'].strip()
            if openlist['token'] == '':
                del openlist['token']
    if openlist['url'].endswith('/'):
        openlist['url'] = openlist['url'][:-1]
    olOld = getAlistById(openlistId)
    if olOld['url'] != openlist['url'] or 'token' in openlist:
        if 'token' not in openlist:
            raise Exception(G('without_token'))
        client = OpenListClient(openlist['url'], openlist['token'], openlistId)
        openlistClientList[openlistId] = client
    updateAlist(openlist)


def addClient(openlist):
    if openlist['remark'] is not None and openlist['remark'].strip() == '':
        openlist['remark'] = None
    if openlist['url'].endswith('/'):
        openlist['url'] = openlist['url'][:-1]
    try:
        client = OpenListClient(openlist['url'], openlist['token'])
        openlistId = addAlist({
            'remark': openlist['remark'],
            'url': openlist['url'],
            'userName': client.user,
            'token': openlist['token']
        })
        client.updateOpenListId(openlistId)
    except Exception as e:
        logger = logging.getLogger()
        logger.error(G('add_alist_client_fail').format(str(e)))
        raise Exception(e)
    else:
        global openlistClientList
        openlistClientList[openlistId] = client


def removeClient(openlistId):
    global openlistClientList
    if openlistId in openlistClientList:
        del openlistClientList[openlistId]
    removeAlist(openlistId)


def getChildPath(openlistId, path):
    client = getClientById(openlistId)
    return client.filePathList(path)