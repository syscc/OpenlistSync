"""Compatibility wrapper for the legacy flat-key language API."""
import threading

from common.commonUtils import readOrSet
from common.locales import getOrSetDefaultLang, t

sysLanguage = None
_local = threading.local()


def set_context_lang(lang=None):
    _local.lang = getOrSetDefaultLang(lang)
    return _local.lang


def get_context_lang():
    return getattr(_local, 'lang', None)


def language(lang=None):
    """Read or update the default language, accepting legacy language names."""
    global sysLanguage
    fileName = 'data/language.txt'
    if lang is None:
        if sysLanguage is None:
            sysLanguage = getOrSetDefaultLang(readOrSet(fileName, 'zh_CN'))
            readOrSet(fileName, sysLanguage, True)
        return sysLanguage
    sysLanguage = getOrSetDefaultLang(lang)
    readOrSet(fileName, sysLanguage, True)


def G(params, lang=None):
    """Return localized text for a legacy flat key."""
    return t(params, lang or get_context_lang() or language())
