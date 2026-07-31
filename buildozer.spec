[app]

title = OpenListSync
package.name = openlistsync
package.domain = com.github

source.dir = .
source.include_exts = py,png,jpg,jpeg,html,js,css,ttf,otf,svg,ico,json,gif,woff,woff2,map,yaml
source.include_patterns = front/**,locales/**,common/**,controller/**,mapper/**,media_tools/**,service/**,doc/config.ini
source.exclude_patterns = .git/**,.venv/**,data/**,tests/**,web/**

version = 0.3.1

requirements = python3,pyjnius,android,tornado,requests,pysocks,urllib3,certifi,chardet,idna,apscheduler,tzlocal,tzdata,setuptools,configparser,pathspec,pyyaml,openssl,sqlite3

orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,WAKE_LOCK,FOREGROUND_SERVICE,REQUEST_IGNORE_BATTERY_OPTIMIZATIONS

android.api = 33
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

android.wakelock = True
android.allow_backup = True
android.apptheme = @android:style/Theme.NoTitleBar
android.presplash_color = #FFFFFF
android.showlog = 0
icon.filename = %(source.dir)s/logo.png
icon.adaptive_foreground.filename = %(source.dir)s/logo_foreground.png
icon.adaptive_background.filename = %(source.dir)s/logo_background.png

p4a.branch = v2024.01.21
p4a.bootstrap = webview
p4a.extra_args = --port=8024

android.release_artifact = apk
android.debug_artifact = apk

log_level = 2

[buildozer]

log_level = 2
warn_on_root = 1
bin_dir = bin
