from mapper import systemConfigMapper


GLOBAL_EXCLUDE_KEY = 'global_exclude'


def normalize_exclude(exclude):
    if exclude is None:
        return None
    if isinstance(exclude, list):
        items = exclude
    else:
        items = str(exclude).split(':')
    items = [str(item).strip() for item in items if str(item).strip()]
    return ':'.join(items) if items else None


def getGlobalExclude():
    return systemConfigMapper.getConfigValue(GLOBAL_EXCLUDE_KEY)


def getConfig():
    return {
        'globalExclude': getGlobalExclude()
    }


def updateConfig(req):
    global_exclude = normalize_exclude(req.get('globalExclude'))
    systemConfigMapper.setConfigValue(GLOBAL_EXCLUDE_KEY, global_exclude)
    return getConfig()
