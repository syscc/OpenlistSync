import json

import requests

from common.LNG import G
from mapper import notifyMapper
from service.notify import sc

NOTIFY_REQUIRED_FIELDS = {
    1: ('sendKey',),
    2: ('url',),
    3: ('corpid', 'corpsecret'),
    4: ('url',),
}


def validateNotify(notify):
    if not isinstance(notify, dict):
        raise Exception(G('notify_config_invalid'))
    method_value = notify.get('method')
    if isinstance(method_value, bool):
        raise Exception(G('notify_method_invalid'))
    if isinstance(method_value, int):
        method = method_value
    elif isinstance(method_value, str) and method_value.isdigit():
        method = int(method_value)
    else:
        raise Exception(G('notify_method_invalid'))
    if method not in range(5):
        raise Exception(G('notify_method_invalid'))

    raw_params = notify.get('params')
    try:
        params = json.loads(raw_params) if isinstance(raw_params, str) else raw_params
    except (TypeError, ValueError):
        raise Exception(G('notify_config_invalid')) from None
    if not isinstance(params, dict):
        raise Exception(G('notify_config_invalid'))

    required = NOTIFY_REQUIRED_FIELDS.get(method, ())
    if method == 0:
        required = ('url', 'method', 'titleName', 'needContent')
    if any(not isinstance(params.get(key), str) or not params[key].strip()
           for key in required if key != 'needContent'):
        raise Exception(G('notify_config_invalid'))
    if method == 0:
        if params.get('needContent') not in (True, False, 0, 1):
            raise Exception(G('notify_config_invalid'))
        request_method = params['method'].upper()
        if request_method not in ('GET', 'POST', 'PUT'):
            raise Exception(G('notify_config_invalid'))
        params['method'] = request_method
        if params['needContent']:
            content_name = params.get('contentName')
            if not isinstance(content_name, str) or not content_name.strip():
                raise Exception(G('notify_config_invalid'))
        if request_method in ('POST', 'PUT') and params.get('contentType') not in (
                'application/json', 'application/x-www-form-urlencoded'):
            raise Exception(G('notify_config_invalid'))
    elif method == 3:
        agent_id = params.get('agentid')
        if (isinstance(agent_id, bool)
                or not isinstance(agent_id, (str, int))
                or not str(agent_id).strip()):
            raise Exception(G('notify_config_invalid'))

    notify['method'] = method
    notify['params'] = json.dumps(params, ensure_ascii=False)
    return params


def _safe_request(request_func, *args, **kwargs):
    try:
        return request_func(*args, **kwargs)
    except requests.RequestException:
        raise Exception(G('notify_request_failed')) from None


def _response_json(response):
    if response.status_code != 200:
        raise Exception(G('notify_response_invalid'))
    try:
        result = response.json()
    except ValueError:
        raise Exception(G('notify_response_invalid')) from None
    if not isinstance(result, dict):
        raise Exception(G('notify_response_invalid'))
    return result


def getNotifyList(needEnable=False):
    """
    获取通知配置列表
    :param needEnable: 是否启用
    :return:
    """
    return notifyMapper.getNotifyList(needEnable)


def addNewNotify(notify):
    """
    新增通知配置
    :param notify:
    :return:
    """
    validateNotify(notify)
    notifyMapper.addNotify(notify)


def editNotify(notify):
    """
    编辑通知配置
    :param notify:
    :return:
    """
    validateNotify(notify)
    notifyMapper.editNotify(notify)


def updateNotifyStatus(notifyId, enable):
    """
    更新通知配置启用状态
    :param notifyId:
    :param enable:
    :return:
    """
    notifyMapper.updateNotifyStatus(notifyId, enable)


def deleteNotify(notifyId):
    """
    删除
    :param notifyId:
    :return:
    """
    notifyMapper.deleteNotify(notifyId)


def testNotify(notify):
    """
    测试通知配置
    :return:
    """
    sendNotify(notify, 'OpenListSync Test',
               G('notify_test_msg'))


def sendNotify(notify, title, content, needNotSync=False):
    """
    发送通知
    :param notify: 通知配置 {'id': 1, 'enable': 1, 'method': 0, // 0-自定义；1-server酱；2-钉钉群机器人；3-企业微信应用消息；4-Lark群机器人
    'params': None, 'createTime': 1732179402}
    :param title: 通知标题
    :param content: 通知内容
    :param needNotSync: 是否是无需同步
    :return:
    method: 不同方法params结构
        0: {'url': 'http://xxx.xx/api', 'method': 'POST', 'contentType': 'application/json',
            'needContent': True, 'titleName': 'title', 'contentName': 'content', 'notSendNull': False}
        1: {'sendKey': 'xxx', 'notSendNull': False}
        2: {'url': '', 'notSendNull': False}
        3: {'corpid': '', 'agentid': '', 'corpsecret': '', 'notSendNull': False}
        4: {'url': '', 'notSendNull': False}
    """
    timeout = (10, 30)
    params = validateNotify(notify)
    # 如果配置了不发送空消息，并且当前状态为无需同步，则不发送通知
    if 'notSendNull' in params and params['notSendNull'] and needNotSync:
        return
    if notify['method'] == 0:
        reqData = {
            params['titleName']: title
        }
        if params['needContent']:
            reqData[params['contentName']] = content
        if params['method'] == 'GET':
            r = _safe_request(requests.get, params['url'], params=reqData, timeout=timeout)
        elif params['method'] == 'POST' or params['method'] == 'PUT':
            if params['contentType'] == 'application/json':
                r = _safe_request(requests.request, params['method'], params['url'], json=reqData, timeout=timeout)
            elif params['contentType'] == 'application/x-www-form-urlencoded':
                r = _safe_request(requests.request, params['method'], params['url'], data=reqData, timeout=timeout)
            else:
                raise Exception("ContentType not allowed")
        else:
            raise Exception("Method not supported")
        if r.status_code != 200:
            raise Exception(G('notify_response_invalid'))
    elif notify['method'] == 1:
        # server酱
        try:
            sc.send(params['sendKey'], title, timeout, content)
        except requests.RequestException:
            raise Exception(G('notify_request_failed')) from None
        except Exception:
            raise Exception(G('notify_response_invalid')) from None
    elif notify['method'] == 2:
        # 钉钉群机器人
        r = _safe_request(requests.post, params['url'], json={
            'msgtype': 'text',
            'text': {
                'content': f'{title}\n\n{content}'
            }
        }, timeout=timeout)
        rst = _response_json(r)
        if rst.get('errcode') != 0:
            raise Exception(rst.get('errmsg') or G('notify_response_invalid'))
    elif notify['method'] == 3:
        # 企业微信应用消息
        # 获取access_token
        token_response = _safe_request(
            requests.get,
            'https://qyapi.weixin.qq.com/cgi-bin/gettoken',
            params={'corpid': params['corpid'], 'corpsecret': params['corpsecret']},
            timeout=timeout)
        token_data = _response_json(token_response)
        if token_data.get('errcode') != 0 or not token_data.get('access_token'):
            raise Exception(token_data.get('errmsg') or G('notify_response_invalid'))
        access_token = token_data['access_token']
        
        # 发送消息
        send_url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send'
        message_data = {
            "touser": params.get('touser') or '@all',
            "msgtype": "text",
            "agentid": params['agentid'],
            "text": {
                "content": f"{title}\n-------------------\n{content}"
            },
            "safe": 0,
            "enable_id_trans": 0,
            "enable_duplicate_check": 0
        }
        
        r = _safe_request(requests.post, send_url, params={'access_token': access_token}, json=message_data,
                          timeout=timeout)
        rst = _response_json(r)
        if rst.get('errcode') != 0:
            raise Exception(rst.get('errmsg') or G('notify_response_invalid'))
    elif notify['method'] == 4:
        # Lark群机器人
        r = _safe_request(requests.post, params['url'], json={
            'msg_type': 'interactive',
            'card': {
                'config': {'wide_screen_mode': True},
                'elements': [{
                    'tag': 'markdown',
                    'content': content
                }],
                'header': {
                    'template': 'blue',
                    'title': {
                        'content': title,
                        'tag': 'plain_text'
                    }
                }
            }
        }, timeout=timeout)
        rst = _response_json(r)
        if rst.get('code') != 0:
            raise Exception(rst.get('msg') or G('notify_response_invalid'))
    else:
        raise Exception(G('notify_method_invalid'))
