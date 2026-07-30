"""
@Author：dr34m
@Date  ：2024/8/16 14:26 
"""
import logging
import os

from common import sqlInit, commonService, locales
from common.config import DEFAULT_PASSWORD, getConfig
from common.LNG import G
from service.syncJob.jobService import initJob
from service.system import logJobService


def init():
    if not os.path.exists('data'):
        os.mkdir('data')
    if not os.path.exists('data/log'):
        os.mkdir('data/log')
    try:
        env_path = os.path.join('data', 'env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith('#'):
                        continue
                    if '=' not in s:
                        continue
                    k, v = s.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if k and v and k not in os.environ:
                        os.environ[k] = v
    except Exception:
        pass
    locales.initLang()
    # 初始化日志
    commonService.setLogger()
    logger = logging.getLogger()
    # 初始化数据库，没有则创建
    passwd = sqlInit.init_sql()
    if passwd is not None:
        if getConfig()['server']['password'] == DEFAULT_PASSWORD:
            msg = G('admin_password_generated').format(passwd)
        else:
            msg = G('admin_password_configured')
        logger.critical(msg)
    logger.info(G('init_sql'))
    # 启动日志文件与任务定时清理任务
    logJobService.startJob()
    # 修改异常中止状态，启动任务
    initJob()
