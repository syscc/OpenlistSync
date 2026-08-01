import hashlib
import json
import logging
import os
import socket
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from common import LNG, config, locales, sqlInit
from common.httpApp import MainIndex, make_app, redact_request_uri, resolve_front_dir
from data import start as sourceStart
from media_tools import openlist_media_renamer as mediaRenamer
from service.mediaScraping import mediaScrapingService
from service.notify import notifyService
from service.openlist.openlistClient import OpenListClient
from service.syncJob import jobClient, jobService, taskService
from service.system import configService, onStart
from service.webhook import refreshService, webhookService


CURRENT_DB_VERSION = 260729


class TemporaryWorkingDirectory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_cwd = os.getcwd()
        self.previous_config = config.sysConfig
        os.chdir(self.temp_dir.name)
        Path('data').mkdir()
        config.sysConfig = None
        LNG.sysLanguage = None
        LNG.set_context_lang('en')

    def tearDown(self):
        config.sysConfig = self.previous_config
        os.chdir(self.previous_cwd)
        self.temp_dir.cleanup()


class LocalizationAndConfigTests(TemporaryWorkingDirectory):
    def test_request_language_context_and_fallback(self):
        LNG.set_context_lang('en-US,en;q=0.9')
        self.assertEqual('Success', LNG.G('success'))
        LNG.set_context_lang('fr-FR,fr;q=0.9')
        self.assertEqual('操作成功', LNG.G('success'))
        LNG.language('eng')
        self.assertEqual('en', LNG.language())
        self.assertEqual('en', Path('data/language.txt').read_text(encoding='utf-8'))

    def test_language_context_is_thread_local(self):
        LNG.set_context_lang('en')
        results = []

        def read_chinese():
            LNG.set_context_lang('zh-CN')
            results.append(LNG.G('success'))

        thread = threading.Thread(target=read_chinese)
        thread.start()
        thread.join()
        self.assertEqual(['操作成功'], results)
        self.assertEqual('Success', LNG.G('success'))

    def test_password_environment_alias_precedence(self):
        with mock.patch.dict(os.environ, {
                'OPENLISTSYNC_PASSWORD': 'brand-password',
                'TAO_PASSWORD': 'tao-password',
                'TAO_PASSWD': 'legacy-password'}, clear=False):
            self.assertEqual('brand-password', config._get_env_password())
        with mock.patch.dict(os.environ, {'TAO_PASSWORD': 'tao-password'}, clear=True):
            self.assertEqual('tao-password', config._get_env_password())
        with mock.patch.dict(os.environ, {'TAO_PASSWD': 'legacy-password'}, clear=True):
            self.assertEqual('legacy-password', config._get_env_password())
        with mock.patch.dict(os.environ, {
                'OPENLISTSYNC_PASSWORD': ' ', 'TAO_PASSWORD': 'tao-password'}, clear=True):
            self.assertEqual('tao-password', config._get_env_password())

    def test_config_file_password_overrides_environment(self):
        Path('data/config.ini').write_text('[OpenlistSync]\npassword=file-password\n', encoding='utf-8')
        with mock.patch.dict(os.environ, {'OPENLISTSYNC_PASSWORD': 'env-password'}, clear=False):
            config.sysConfig = None
            self.assertEqual('file-password', config.getConfig()['server']['password'])

    def test_config_file_task_timeout_alias_is_honored(self):
        Path('data/config.ini').write_text('[OpenlistSync]\ntask_timeout=36\n', encoding='utf-8')
        config.sysConfig = None
        self.assertEqual(36, config.getConfig()['server']['timeout'])

    def test_startup_logs_generated_password_but_not_configured_password(self):
        logger = logging.getLogger()
        for configured_password, generated_password, expected, hidden in (
                (config.DEFAULT_PASSWORD, 'random-password', 'random-password', None),
                ('configured-password', 'configured-password', 'configured administrator password',
                 'configured-password')):
            config.sysConfig = {
                'server': {'password': configured_password},
                'db': {'dbname': str(Path(self.temp_dir.name) / 'unused.db')},
            }
            with self.subTest(configured_password=configured_password), mock.patch.object(
                    onStart.locales, 'initLang'), mock.patch.object(
                    onStart.commonService, 'setLogger'), mock.patch.object(
                    onStart.sqlInit, 'init_sql', return_value=generated_password), mock.patch.object(
                    onStart.logJobService, 'startJob'), mock.patch.object(
                    onStart, 'initJob'), mock.patch.object(logger, 'critical') as critical:
                onStart.init()
            message = critical.call_args.args[0]
            self.assertIn(expected, message)
            if hidden is not None:
                self.assertNotIn(hidden, message)


class SourceStartTests(unittest.TestCase):
    def test_frontend_install_and_launch_use_vue3_web_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            web_dir = base / 'web'
            web_dir.mkdir()
            (web_dir / 'package.json').write_text('{}', encoding='utf-8')
            (web_dir / 'package-lock.json').write_text('{}', encoding='utf-8')

            with mock.patch.object(sourceStart, 'find_npm', return_value='npm'), \
                    mock.patch.object(sourceStart, 'run', return_value=True) as run_mock:
                self.assertTrue(sourceStart.install_frontend_deps(base))
            self.assertEqual(str(web_dir), run_mock.call_args.kwargs['cwd'])
            self.assertEqual(['npm', 'ci'], run_mock.call_args.args[0])

            process = mock.Mock(pid=123)
            with mock.patch.object(sourceStart, 'find_listen_pid_by_port', return_value=None), \
                    mock.patch.object(sourceStart, 'find_npm', return_value='npm'), \
                    mock.patch.object(sourceStart.subprocess, 'Popen', return_value=process) as popen_mock, \
                    mock.patch.object(sourceStart, 'write_pid'), \
                    mock.patch('builtins.print'):
                self.assertIs(process, sourceStart.start_frontend(base))
            self.assertEqual(str(web_dir), popen_mock.call_args.kwargs['cwd'])
            popen_mock.call_args.kwargs['stdout'].close()

    def test_existing_port_listener_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            with mock.patch.object(sourceStart, 'read_configured_backend_port', return_value=8023), \
                    mock.patch.object(sourceStart, 'find_listen_pid_by_port', return_value=321), \
                    mock.patch.object(sourceStart, 'write_pid') as write_pid_mock, \
                    mock.patch('builtins.print'):
                self.assertIsNone(sourceStart.start_backend(base))
                self.assertIsNone(sourceStart.start_frontend(base))
            write_pid_mock.assert_not_called()

    def test_stop_only_targets_services_recorded_by_source_script(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            with mock.patch.object(sourceStart, 'project_root', return_value=base), \
                    mock.patch.object(sourceStart, 'find_listen_pid_by_port') as find_pid_mock, \
                    mock.patch.object(sourceStart, 'stop_pid', return_value=False) as stop_pid_mock, \
                    mock.patch('builtins.print'):
                sourceStart.stop()
            find_pid_mock.assert_not_called()
            self.assertEqual(2, stop_pid_mock.call_count)
            self.assertTrue(all(call.args[0] is None for call in stop_pid_mock.call_args_list))


class DatabaseMigrationTests(TemporaryWorkingDirectory):
    def _use_database(self, path, password=config.DEFAULT_PASSWORD):
        config.sysConfig = {
            'db': {'dbname': str(path)},
            'server': {'passwdStr': 'test-pepper', 'password': password},
        }

    @staticmethod
    def _columns(conn, table):
        return {row[1] for row in conn.execute(f'PRAGMA table_info({table})')}

    def test_fresh_database_uses_configured_admin_password(self):
        db_path = Path(self.temp_dir.name) / 'fresh.db'
        self._use_database(db_path, 'configured-password')
        returned_password = sqlInit.init_sql()
        self.assertEqual('configured-password', returned_password)
        with sqlite3.connect(db_path) as conn:
            stored = conn.execute("select passwd from user_list where userName='admin'").fetchone()[0]
            expected = hashlib.md5(b'configured-passwordtest-pepper').hexdigest()
            self.assertEqual(expected, stored)
            self.assertEqual(CURRENT_DB_VERSION, conn.execute('select sqlVersion from user_list').fetchone()[0])
            self.assertTrue({'openlistId', 'minFileSize', 'maxFileSize'} <= self._columns(conn, 'job'))
            self.assertIn('openlistTaskId', self._columns(conn, 'job_task_item'))

    def test_upstream_260715_schema_is_reconciled_without_data_loss(self):
        db_path = Path(self.temp_dir.name) / 'upstream.db'
        with sqlite3.connect(db_path) as conn:
            conn.executescript("""
                create table user_list(id integer primary key, userName text, passwd text, sqlVersion integer);
                insert into user_list values(1, 'admin', 'hash', 260715);
                create table alist_list(id integer primary key, remark text, url text, userName text, token text,
                    createTime integer, unique(url, userName));
                insert into alist_list values(7, 'upstream', 'http://example', 'admin', 'token', 123);
                create table job(id integer primary key, alistId integer, minFileSize integer, maxFileSize integer);
                insert into job values(9, 7, 10, 100);
                create table job_task_item(id integer primary key, alistTaskId text);
                insert into job_task_item values(11, 'copy-task');
            """)
        self._use_database(db_path)
        sqlInit.init_sql()
        with sqlite3.connect(db_path) as conn:
            tables = {row[0] for row in conn.execute("select name from sqlite_master where type='table'")}
            self.assertIn('list', tables)
            self.assertEqual((7, 'upstream', 'token'),
                             conn.execute('select id, remark, token from list').fetchone())
            self.assertTrue({'openlistId', 'minFileSize', 'maxFileSize'} <= self._columns(conn, 'job'))
            self.assertEqual((7, 10, 100),
                             conn.execute('select openlistId, minFileSize, maxFileSize from job').fetchone())
            self.assertIn('openlistTaskId', self._columns(conn, 'job_task_item'))
            self.assertEqual('copy-task', conn.execute('select openlistTaskId from job_task_item').fetchone()[0])
            self.assertIn('system_config', tables)
            for table in ('media_scraping_job', 'media_scraping_task', 'media_scraping_task_item'):
                self.assertIn(table, tables)
                self.assertIn('id', self._columns(conn, table))
            self.assertEqual(CURRENT_DB_VERSION, conn.execute('select sqlVersion from user_list').fetchone()[0])

    def test_existing_custom_tables_and_rows_are_preserved(self):
        db_path = Path(self.temp_dir.name) / 'custom.db'
        with sqlite3.connect(db_path) as conn:
            conn.executescript("""
                create table user_list(id integer primary key, userName text, passwd text, sqlVersion integer);
                insert into user_list values(1, 'admin', 'hash', 260729);
                create table list(id integer primary key, remark text, url text, userName text, token text);
                insert into list values(3, 'current', 'http://openlist', 'admin', 'keep-token');
                create table job(id integer primary key, openlistId integer);
                insert into job values(4, 3);
                create table job_task_item(id integer primary key, openlistTaskId text);
                insert into job_task_item values(5, 'keep-task');
                create table system_config(key text primary key, value text);
                insert into system_config values('global_exclude', '*.tmp');
                create table media_scraping_job(id integer primary key, groupKey text unique);
                insert into media_scraping_job values(6, 'keep-group');
                create table media_scraping_task(id integer primary key, path text);
                insert into media_scraping_task values(7, '/keep/task');
                create table media_scraping_task_item(id integer primary key, taskId integer, srcPath text);
                insert into media_scraping_task_item values(8, 7, '/keep/item');
            """)
        self._use_database(db_path)
        sqlInit.init_sql()
        with sqlite3.connect(db_path) as conn:
            self.assertEqual('keep-token', conn.execute('select token from list where id=3').fetchone()[0])
            self.assertEqual('*.tmp', conn.execute(
                "select value from system_config where key='global_exclude'").fetchone()[0])
            self.assertIn('updateTime', self._columns(conn, 'system_config'))
            self.assertEqual('keep-group', conn.execute(
                'select groupKey from media_scraping_job where id=6').fetchone()[0])
            self.assertTrue({'request', 'latestTaskId', 'openlistId'} <=
                            self._columns(conn, 'media_scraping_job'))
            self.assertEqual('/keep/task', conn.execute(
                'select path from media_scraping_task where id=7').fetchone()[0])
            self.assertTrue({'jobId', 'taskName', 'request', 'updateTime'} <=
                            self._columns(conn, 'media_scraping_task'))
            self.assertEqual('/keep/item', conn.execute(
                'select srcPath from media_scraping_task_item where id=8').fetchone()[0])
            self.assertTrue({'targetPath', 'status', 'errMsg'} <=
                            self._columns(conn, 'media_scraping_task_item'))
            self.assertTrue({'minFileSize', 'maxFileSize'} <= self._columns(conn, 'job'))
            self.assertIn('openlistTaskId', self._columns(conn, 'job_task_item'))


class JobFilteringTests(unittest.TestCase):
    def setUp(self):
        LNG.set_context_lang('en')

    def test_file_size_validation(self):
        self.assertEqual(0, jobService.normalizeFileSize('0'))
        self.assertEqual(42, jobService.normalizeFileSize(42.0))
        self.assertIsNone(jobService.normalizeFileSize(None))
        for invalid in (True, -1, 1.2, '1.5', str(jobService.MAX_SQLITE_INTEGER + 1)):
            with self.subTest(invalid=invalid), self.assertRaises(Exception):
                jobService.normalizeFileSize(invalid)
        job = {'isCron': 2, 'enable': 1, 'exclude': None, 'minFileSize': '101', 'maxFileSize': 100}
        with self.assertRaisesRegex(Exception, 'minimum file size'):
            jobService.cleanJobInput(job)

    def test_sync_filters_copy_and_full_sync_deletion(self):
        task = object.__new__(jobClient.JobTask)
        task.job = {'method': 1, 'minFileSize': 10, 'maxFileSize': 100}
        task.breakFlag = False
        listings = {
            '/src/': {'small.bin': 5, 'copy.bin': 50},
            '/dst/': {'small.bin': 5, 'copy.bin': 40, 'low.bin': 4, 'delete.bin': 60, 'only/': None},
            '/dst/only/': {'low.bin': 1, 'delete.bin': 20, 'high.bin': 101, 'nested/': None},
            '/dst/only/nested/': {'delete-too.bin': 30},
        }
        task.listDir = mock.Mock(side_effect=lambda path, *args, **kwargs: listings[path])
        task.copyFile = mock.Mock()
        task.delFile = mock.Mock()

        task.syncWithHave('/src/', '/dst/', None, '/src/', '/dst/', True)

        task.copyFile.assert_called_once_with('/src/', '/dst/', 'copy.bin', 50)
        self.assertCountEqual(task.delFile.call_args_list, [
            mock.call('/dst/', 'delete.bin', 60),
            mock.call('/dst/only/', 'delete.bin', 20),
            mock.call('/dst/only/nested/', 'delete-too.bin', 30),
        ])

    def test_scheduler_uses_fifteen_minute_misfire_grace(self):
        scheduler = mock.Mock()
        scheduler.add_job.return_value = mock.Mock()
        client = object.__new__(jobClient.JobClient)
        client.job = {'isCron': 0, 'interval': 5, 'enable': 1}
        client.doJob = mock.Mock()
        with mock.patch.object(jobClient, 'BackgroundScheduler', return_value=scheduler):
            client.doByTime()
        self.assertEqual(15 * 60, scheduler.add_job.call_args.kwargs['misfire_grace_time'])


class ApiCompatibilityTests(unittest.TestCase):
    def test_main_index_renders_relative_frontend_from_absolute_path(self):
        with tempfile.TemporaryDirectory(dir='.') as temp_dir:
            front_dir = os.path.relpath(temp_dir)
            index_path = os.path.join(front_dir, 'index.html')
            Path(index_path).write_text('web', encoding='utf-8')
            handler = object.__new__(MainIndex)
            handler.front_dir = front_dir
            with mock.patch.object(MainIndex, 'render') as render:
                handler.get()
            render.assert_called_once_with(os.path.abspath(index_path))

    def test_access_log_redacts_sensitive_query_values(self):
        uri = redact_request_uri('/webhook?apikey=private-key&title=Ready%20Now&token=secret')
        self.assertNotIn('private-key', uri)
        self.assertNotIn('secret', uri)
        self.assertIn('title=Ready+Now', uri)
        self.assertEqual(2, uri.count('%3Credacted%3E'))

    def test_shared_http_app_keeps_openlist_custom_routes(self):
        app = make_app({'passwdStr': 'test-secret'}, '/tmp/missing-front')
        patterns = [rule.matcher.regex.pattern for rule in app.default_router.rules[0].target.rules]
        self.assertIn('/svr/openlist$', patterns)
        self.assertIn('/svr/media/scraping$', patterns)
        self.assertIn('/svr/system/config$', patterns)
        self.assertIn('/svr/system/proxy/reveal$', patterns)
        self.assertIn('/svr/system/proxy/test$', patterns)
        self.assertIn('/webhook$', patterns)
        self.assertNotIn('/svr/alist$', patterns)

    def test_frontend_resolution_prefers_built_web_when_front_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            (base / 'web' / 'dist').mkdir(parents=True)
            (base / 'web' / 'dist' / 'index.html').write_text('web', encoding='utf-8')
            self.assertEqual(str(base / 'web' / 'dist'), resolve_front_dir(str(base)))
            (base / 'front').mkdir()
            (base / 'front' / 'index.html').write_text('front', encoding='utf-8')
            self.assertEqual(str(base / 'front'), resolve_front_dir(str(base)))

    def test_paged_job_responses_include_legacy_and_vue3_list_names(self):
        jobs = [{'id': 1}]
        with mock.patch.object(jobService.jobMapper, 'getJobList', return_value={
                'list': jobs, 'count': 1}):
            result = jobService.getJobList({})
        self.assertEqual(jobs, result['jobList'])
        self.assertIs(result['jobList'], result['dataList'])

        tasks = [{'id': 2, 'status': 2, 'taskNum': json.dumps({
            'waitNum': 0, 'runningNum': 0, 'successNum': 1,
            'failNum': 0, 'otherNum': 0, 'allNum': 1})}]
        with mock.patch.object(taskService.jobMapper, 'getJobTaskList', return_value={
                'list': tasks, 'count': 1}):
            result = taskService.getTaskList({})
        self.assertEqual(tasks, result['taskList'])
        self.assertIs(result['taskList'], result['dataList'])

        task_items = [{'id': 3}]
        with mock.patch.object(taskService.jobMapper, 'getJobTaskItemList', return_value={
                'list': task_items, 'count': 1}), mock.patch.object(
                taskService.jobMapper, 'getJobByTaskId', return_value={'id': 1}):
            result = taskService.getTaskItemList({'taskId': 2})
        self.assertEqual(task_items, result['taskItemList'])
        self.assertIs(result['taskItemList'], result['dataList'])

    def test_openlist_exact_path_check_forces_refresh(self):
        client = OpenListClient.__new__(OpenListClient)
        client.post = mock.Mock(return_value={'is_dir': True})

        self.assertTrue(client.pathExists('/media/tv/Show (2026)', True))
        client.post.assert_called_once_with('/api/fs/get', data={
            'path': '/media/tv/Show (2026)',
            'refresh': True,
        })


class TmdbConfigurationTests(unittest.TestCase):
    def test_proxy_reveal_returns_full_connection_string_on_demand(self):
        saved_url = 'http://proxy-user:stored-secret@proxy.local:8080'
        store = {
            configService.PROXY_SERVER_KEY: json.dumps({
                'enabled': True,
                'url': saved_url,
            }),
        }
        with mock.patch.object(
                configService.systemConfigMapper,
                'getConfigValue',
                side_effect=lambda key: store.get(key)):
            public = configService.getConfig()['proxyServer']
            revealed = configService.revealProxyServer()

        self.assertEqual('http://proxy-user@proxy.local:8080', public['url'])
        self.assertNotIn('stored-secret', json.dumps(public))
        self.assertEqual({'url': saved_url}, revealed)

    def test_system_config_migrates_legacy_proxy_and_preserves_redacted_password(self):
        store = {
            configService.GLOBAL_EXCLUDE_KEY: '*.tmp',
            configService.TMDB_PROXY_KEY: json.dumps({
                'enabled': True,
                'type': 'http',
                'host': 'old-proxy.local',
                'port': 8080,
                'username': 'old-user',
                'password': 'stored-secret',
            }),
        }

        def set_value(key, value):
            store[key] = value

        with mock.patch.object(
                configService.systemConfigMapper,
                'getConfigValue',
                side_effect=lambda key: store.get(key)), mock.patch.object(
                configService.systemConfigMapper,
                'setConfigValue',
                side_effect=set_value):
            result = configService.getConfig()
            self.assertEqual({
                'enabled': True,
                'url': 'http://old-user@old-proxy.local:8080',
                'passwordSet': True,
            }, result['proxyServer'])
            self.assertNotIn('stored-secret', json.dumps(result))

            result = configService.updateConfig({
                'proxyServer': {
                    'enabled': False,
                    'url': result['proxyServer']['url'],
                },
            })
            saved_proxy = json.loads(store[configService.PROXY_SERVER_KEY])
            self.assertFalse(saved_proxy['enabled'])
            self.assertEqual(
                'http://old-user:stored-secret@old-proxy.local:8080',
                saved_proxy['url'],
            )
            self.assertFalse(result['proxyServer']['enabled'])
            self.assertTrue(result['proxyServer']['passwordSet'])
            self.assertEqual('*.tmp', store[configService.GLOBAL_EXCLUDE_KEY])

            previous_proxy = store[configService.PROXY_SERVER_KEY]
            result = configService.updateConfig({'globalExclude': ['*.nfo', '@eaDir']})
            self.assertEqual('*.nfo:@eaDir', result['globalExclude'])
            self.assertEqual(previous_proxy, store[configService.PROXY_SERVER_KEY])

    def test_system_config_accepts_proxy_url_auth_variants_and_new_key_wins(self):
        cases = [
            ('http://proxy.local:8080', 'http://proxy.local:8080', False),
            (
                'http://user%20name:p@ss@proxy.local:8080',
                'http://user%20name:p%40ss@proxy.local:8080',
                True,
            ),
            ('http://:password@proxy.local:3128', 'http://:password@proxy.local:3128', True),
            ('socks://proxy.local:1080', 'socks://proxy.local:1080', False),
            ('socks://user:password@[2001:db8::1]:1080', 'socks://user:password@[2001:db8::1]:1080', True),
        ]
        for value, expected, password_set in cases:
            store = {
                configService.TMDB_PROXY_KEY: json.dumps({
                    'enabled': True,
                    'type': 'http',
                    'host': 'legacy.local',
                    'port': 8080,
                }),
            }
            with self.subTest(value=value), mock.patch.object(
                    configService.systemConfigMapper,
                    'getConfigValue',
                    side_effect=lambda key: store.get(key)), mock.patch.object(
                    configService.systemConfigMapper,
                    'setConfigValue',
                    side_effect=lambda key, saved: store.__setitem__(key, saved)):
                result = configService.updateConfig({
                    'proxyServer': {'enabled': True, 'url': value},
                })
                saved = json.loads(store[configService.PROXY_SERVER_KEY])
                self.assertEqual(expected, saved['url'])
                self.assertTrue(saved['enabled'])
                self.assertEqual(password_set, result['proxyServer']['passwordSet'])
                self.assertEqual(
                    saved,
                    configService.getProxyServer(),
                )

    def test_proxy_server_new_key_precedes_legacy_and_invalid_new_value_fails_closed(self):
        legacy = json.dumps({
            'enabled': False,
            'type': 'http',
            'host': 'legacy.local',
            'port': 8080,
            'username': 'legacy-user',
            'password': 'legacy-secret',
        })
        store = {configService.TMDB_PROXY_KEY: legacy}
        with mock.patch.object(
                configService.systemConfigMapper,
                'getConfigValue',
                side_effect=lambda key: store.get(key)):
            self.assertEqual({
                'enabled': False,
                'url': 'http://legacy-user:legacy-secret@legacy.local:8080',
            }, configService.getProxyServer())

            store[configService.PROXY_SERVER_KEY] = json.dumps({
                'enabled': False,
                'url': 'socks://new.local:1080',
            })
            self.assertEqual({
                'enabled': False,
                'url': 'socks://new.local:1080',
            }, configService.getProxyServer())

            store[configService.PROXY_SERVER_KEY] = '{invalid json'
            self.assertEqual({
                'enabled': False,
                'url': '',
            }, configService.getProxyServer())

    def test_legacy_proxy_post_preserves_password_only_for_same_endpoint(self):
        store = {
            configService.PROXY_SERVER_KEY: json.dumps({
                'enabled': True,
                'url': 'http://old-user:stored-secret@old.local:8080',
            }),
        }
        with mock.patch.object(
                configService.systemConfigMapper,
                'getConfigValue',
                side_effect=lambda key: store.get(key)), mock.patch.object(
                configService.systemConfigMapper,
                'setConfigValue',
                side_effect=lambda key, value: store.__setitem__(key, value)):
            configService.updateConfig({
                'tmdbProxy': {
                    'enabled': False,
                    'type': 'http',
                    'host': 'old.local',
                    'port': 8080,
                    'username': 'old-user',
                    'password': '',
                },
            })
            saved = json.loads(store[configService.PROXY_SERVER_KEY])
            self.assertEqual('http://old-user:stored-secret@old.local:8080', saved['url'])
            self.assertFalse(saved['enabled'])

            configService.updateConfig({
                'tmdbProxy': {
                    'enabled': True,
                    'type': 'socks5',
                    'host': 'new.local',
                    'port': 1080,
                    'username': '',
                    'password': '',
                },
            })

        saved = json.loads(store[configService.PROXY_SERVER_KEY])
        self.assertEqual('socks://new.local:1080', saved['url'])
        self.assertTrue(saved['enabled'])

    def test_legacy_proxy_post_parses_string_enabled_value(self):
        store = {
            configService.PROXY_SERVER_KEY: json.dumps({
                'enabled': True,
                'url': 'http://proxy.local:8080',
            }),
        }
        with mock.patch.object(
                configService.systemConfigMapper,
                'getConfigValue',
                side_effect=lambda key: store.get(key)), mock.patch.object(
                configService.systemConfigMapper,
                'setConfigValue',
                side_effect=lambda key, value: store.__setitem__(key, value)):
            configService.updateConfig({
                'tmdbProxy': {'enabled': 'false'},
            })

        saved = json.loads(store[configService.PROXY_SERVER_KEY])
        self.assertFalse(saved['enabled'])
        self.assertEqual('http://proxy.local:8080', saved['url'])

    def test_proxy_server_changed_endpoint_does_not_reuse_password(self):
        cases = [
            'http://old-user@new.local:8080',
            'socks://old-user@old.local:8080',
            'http://new-user@old.local:8080',
        ]
        for new_url in cases:
            store = {
                configService.PROXY_SERVER_KEY: json.dumps({
                    'enabled': True,
                    'url': 'http://old-user:stored-secret@old.local:8080',
                }),
            }
            with self.subTest(new_url=new_url), mock.patch.object(
                    configService.systemConfigMapper,
                    'getConfigValue',
                    side_effect=lambda key: store.get(key)), mock.patch.object(
                    configService.systemConfigMapper,
                    'setConfigValue',
                    side_effect=lambda key, value: store.__setitem__(key, value)):
                result = configService.updateConfig({
                    'proxyServer': {'enabled': True, 'url': new_url},
                })

            saved = json.loads(store[configService.PROXY_SERVER_KEY])
            self.assertEqual(new_url, saved['url'])
            self.assertFalse(result['proxyServer']['passwordSet'])

    def test_system_config_rejects_invalid_proxy_urls(self):
        cases = [
            '',
            'proxy.local:8080',
            'ftp://proxy.local:21',
            'http://proxy.local',
            'http://proxy.local:0',
            'http://proxy.local:65536',
            'http://proxy.local:invalid',
            'http://proxy local:8080',
            'http://proxy.local:8080/path',
            'http://proxy.local:8080?query=1',
            'http://proxy.local:8080#fragment',
            'socks5://proxy.local:1080',
            'http://[abc]:8080',
            'socks://2001:db8::1:1080',
        ]
        for value in cases:
            with self.subTest(value=value), mock.patch.object(
                    configService.systemConfigMapper,
                    'getConfigValue',
                    return_value=None), mock.patch.object(
                    configService.systemConfigMapper,
                    'setConfigValue') as set_mock:
                with self.assertRaisesRegex(Exception, 'Proxy server'):
                    configService.updateConfig({
                        'proxyServer': {'enabled': True, 'url': value},
                    })
                set_mock.assert_not_called()

    def test_proxy_latency_test_uses_submitted_url_without_persisting(self):
        response = mock.Mock(status_code=204)
        session = mock.Mock()
        session.get.return_value = response
        client = mock.Mock()
        client.session = session
        client.proxies = {
            'http': 'http://new-proxy.local:8080',
            'https': 'http://new-proxy.local:8080',
        }

        with mock.patch.object(
                configService,
                'getProxyServer',
                return_value={'enabled': False, 'url': ''}), mock.patch.object(
                configService.mediaRenamer,
                'TMDbClient',
                return_value=client) as client_class, mock.patch.object(
                configService.time,
                'monotonic',
                side_effect=[10.0, 10.123]):
            result = configService.testProxyServer({
                'url': 'http://new-proxy.local:8080',
            })

        self.assertEqual({
            'url': configService.PROXY_TEST_URL,
            'latencyMs': 123,
            'statusCode': 204,
        }, result)
        client_class.assert_called_once_with(proxy={'url': 'http://new-proxy.local:8080'})
        session.get.assert_called_once_with(
            configService.PROXY_TEST_URL,
            timeout=configService.PROXY_TEST_TIMEOUT,
            proxies=client.proxies,
            allow_redirects=False,
        )
        response.close.assert_called_once_with()
        session.close.assert_called_once_with()

    def test_proxy_latency_test_uses_direct_connection_without_proxy_url(self):
        response = mock.Mock(status_code=204)
        session = mock.Mock()
        session.get.return_value = response

        with mock.patch.object(
                configService,
                'getProxyServer',
                return_value={'enabled': False, 'url': ''}), mock.patch.object(
                configService.mediaRenamer.requests,
                'Session',
                return_value=session), mock.patch.object(
                configService.time,
                'monotonic',
                side_effect=[10.0, 10.123]):
            result = configService.testProxyServer({})

        self.assertEqual({
            'url': configService.PROXY_TEST_URL,
            'latencyMs': 123,
            'statusCode': 204,
        }, result)
        self.assertFalse(session.trust_env)
        session.get.assert_called_once_with(
            configService.PROXY_TEST_URL,
            timeout=configService.PROXY_TEST_TIMEOUT,
            proxies={},
            allow_redirects=False,
        )
        response.close.assert_called_once_with()
        session.close.assert_called_once_with()

    def test_proxy_latency_test_preserves_saved_credentials_for_redacted_url(self):
        response = mock.Mock(status_code=204)
        session = mock.Mock()
        session.get.return_value = response
        client = mock.Mock()
        client.session = session
        client.proxies = {}
        saved_url = 'http://proxy-user:stored-secret@proxy.local:8080'

        with mock.patch.object(
                configService,
                'getProxyServer',
                return_value={'enabled': True, 'url': saved_url}), mock.patch.object(
                configService.mediaRenamer,
                'TMDbClient',
                return_value=client) as client_class:
            configService.testProxyServer({'url': 'http://proxy-user@proxy.local:8080'})

        client_class.assert_called_once_with(proxy={'url': saved_url})

    def test_proxy_latency_test_redacts_request_errors(self):
        session = mock.Mock()
        session.get.side_effect = configService.mediaRenamer.requests.ConnectionError(
            'failed via http://proxy-user:stored-secret@proxy.local:8080'
        )
        client = mock.Mock()
        client.session = session
        client.proxies = {}
        client._redact_error.return_value = 'failed via <redacted>'

        with mock.patch.object(
                configService,
                'getProxyServer',
                return_value={'enabled': True, 'url': 'http://proxy.local:8080'}), mock.patch.object(
                configService.mediaRenamer,
                'TMDbClient',
                return_value=client):
            with self.assertRaises(Exception) as caught:
                configService.testProxyServer({})

        self.assertIn('Proxy test failed: failed via <redacted>', str(caught.exception))
        self.assertNotIn('stored-secret', str(caught.exception))
        session.close.assert_called_once_with()

    def test_proxy_latency_test_rejects_non_204_responses(self):
        for status_code in (200, 302, 407):
            with self.subTest(status_code=status_code):
                response = mock.Mock(status_code=status_code)
                session = mock.Mock()
                session.get.return_value = response
                client = mock.Mock()
                client.session = session
                client.proxies = {}

                with mock.patch.object(
                        configService,
                        'getProxyServer',
                        return_value={'enabled': True, 'url': 'http://proxy.local:8080'}), mock.patch.object(
                        configService.mediaRenamer,
                        'TMDbClient',
                        return_value=client):
                    with self.assertRaisesRegex(Exception, r'expected HTTP 204'):
                        configService.testProxyServer({})

                response.close.assert_called_once_with()
                session.close.assert_called_once_with()

    def test_media_config_defaults_and_normalizes_tmdb_api_url(self):
        self.assertEqual(
            'https://api.themoviedb.org',
            mediaScrapingService._default_config()['tmdbApiUrl'],
        )
        cases = [
            ('', 'https://api.themoviedb.org'),
            ('api.tmdb.org/', 'https://api.tmdb.org'),
            ('https://api.themoviedb.org/3/', 'https://api.themoviedb.org'),
            ('http://mirror.example/tmdb/', 'http://mirror.example/tmdb'),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                normalized = mediaScrapingService._normalize_config({'tmdbApiUrl': value})
                self.assertEqual(expected, normalized['tmdbApiUrl'])

        for value in (
                'ftp://api.tmdb.org',
                'https://user:password@api.tmdb.org',
                'https://api.tmdb.org?api_key=secret'):
            with self.subTest(value=value), self.assertRaises(mediaRenamer.TMDbError):
                mediaScrapingService._normalize_config({'tmdbApiUrl': value})

    def test_runner_config_reads_current_proxy_only_for_tmdb(self):
        config_data = mediaScrapingService._normalize_config({
            'tmdbApiKey': 'tmdb-key',
            'tmdbApiUrl': 'api.tmdb.org',
        })
        openlist = {
            'url': 'https://openlist.example',
            'token': 'openlist-token',
        }
        http_proxy = {'enabled': True, 'url': 'http://first-proxy.local:8080'}
        socks_proxy = {'enabled': True, 'url': 'socks://second-proxy.local:1080'}
        with mock.patch.object(
                mediaScrapingService.configService,
                'getProxyServer',
                side_effect=[http_proxy, socks_proxy]) as get_proxy:
            first = mediaScrapingService._build_runner_config(config_data, openlist)
            second = mediaScrapingService._build_runner_config(config_data, openlist)

        self.assertEqual(2, get_proxy.call_count)
        self.assertEqual({'url': http_proxy['url']}, first['tmdb']['proxy'])
        self.assertEqual({'url': socks_proxy['url']}, second['tmdb']['proxy'])
        self.assertEqual('https://api.tmdb.org', first['tmdb']['api_base_url'])
        self.assertNotIn('proxy', first['openlist'])


class TmdbClientTests(unittest.TestCase):
    def test_tmdb_request_uses_custom_url_and_scoped_http_or_socks5_proxy(self):
        cases = [
            (
                {'url': 'http://user%20name:p%40ss%2Fword@proxy.local:8080'},
                'http://user%20name:p%40ss%2Fword@proxy.local:8080',
            ),
            (
                {'url': 'socks://[2001:db8::1]:1080'},
                'socks5h://[2001:db8::1]:1080',
            ),
            (
                {'url': 'http://:password@proxy.local:3128'},
                'http://:password@proxy.local:3128',
            ),
            (
                {'url': 'socks://proxy.local:1080'},
                'socks5h://proxy.local:1080',
            ),
            (
                {'url': 'socks://:password@proxy.local:1080'},
                'socks5h://:password@proxy.local:1080',
            ),
        ]
        for proxy, expected_proxy_url in cases:
            with self.subTest(proxy=proxy['url']):
                response = mock.Mock(status_code=200, text='{"results": []}')
                session = mock.Mock()
                session.get.return_value = response
                client = mediaRenamer.TMDbClient(
                    api_key='api-secret',
                    api_base_url='https://mirror.example/tmdb/3/',
                    proxy=proxy,
                    session=session,
                )

                result = client.request('/search/movie', {'query': 'Dune'})

                self.assertEqual({'results': []}, result)
                self.assertFalse(session.trust_env)
                session.get.assert_called_once()
                url = session.get.call_args.args[0]
                request_options = session.get.call_args.kwargs
                self.assertEqual(
                    'https://mirror.example/tmdb/3/search/movie',
                    url,
                )
                self.assertEqual({
                    'http': expected_proxy_url,
                    'https': expected_proxy_url,
                }, request_options['proxies'])
                self.assertEqual('Dune', request_options['params']['query'])
                self.assertEqual('api-secret', request_options['params']['api_key'])
                response.close.assert_called_once_with()

    def test_socks_password_only_sends_empty_username_and_password(self):
        captured = {}
        server_errors = []
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(3)
        proxy_port = listener.getsockname()[1]

        def recv_exact(conn, size):
            data = b''
            while len(data) < size:
                chunk = conn.recv(size - len(data))
                if not chunk:
                    raise EOFError('SOCKS client closed the connection')
                data += chunk
            return data

        def serve_proxy():
            try:
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(3)
                    greeting = recv_exact(conn, 2)
                    captured['methods'] = recv_exact(conn, greeting[1])
                    conn.sendall(b'\x05\x02')

                    auth_header = recv_exact(conn, 2)
                    captured['username'] = recv_exact(conn, auth_header[1])
                    password_length = recv_exact(conn, 1)[0]
                    captured['password'] = recv_exact(conn, password_length)
                    conn.sendall(b'\x01\x00')

                    request_header = recv_exact(conn, 4)
                    if request_header[3] != 3:
                        raise AssertionError(f'unexpected address type: {request_header[3]}')
                    host_length = recv_exact(conn, 1)[0]
                    captured['target'] = (
                        recv_exact(conn, host_length),
                        int.from_bytes(recv_exact(conn, 2), 'big'),
                    )
                    conn.sendall(b'\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x00')

                    request = b''
                    while b'\r\n\r\n' not in request:
                        request += conn.recv(4096)
                    captured['requestLine'] = request.split(b'\r\n', 1)[0]
                    body = b'{"results": []}'
                    conn.sendall(
                        b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n'
                        + f'Content-Length: {len(body)}\r\n'.encode()
                        + b'Connection: close\r\n\r\n'
                        + body
                    )
            except Exception as exc:
                server_errors.append(exc)
            finally:
                listener.close()

        thread = threading.Thread(target=serve_proxy, daemon=True)
        thread.start()
        try:
            client = mediaRenamer.TMDbClient(
                api_key='api-secret',
                api_base_url='http://tmdb.test',
                proxy={'url': f'socks://:only-secret@127.0.0.1:{proxy_port}'},
            )
            result = client.request('configuration')
        finally:
            thread.join(timeout=3)

        self.assertFalse(thread.is_alive())
        self.assertEqual([], server_errors)
        self.assertEqual({'results': []}, result)
        self.assertEqual(b'\x00\x02', captured['methods'])
        self.assertEqual(b'', captured['username'])
        self.assertEqual(b'only-secret', captured['password'])
        self.assertEqual((b'tmdb.test', 80), captured['target'])
        self.assertEqual(b'GET /3/configuration?language=zh-CN&api_key=api-secret HTTP/1.1',
                         captured['requestLine'])

    def test_http_password_only_sends_proxy_authorization(self):
        captured = {}
        server_errors = []
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(3)
        proxy_port = listener.getsockname()[1]

        def serve_proxy():
            try:
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(3)
                    request = b''
                    while b'\r\n\r\n' not in request:
                        request += conn.recv(4096)
                    lines = request.split(b'\r\n')
                    captured['requestLine'] = lines[0]
                    captured['authorization'] = next(
                        line.split(b': ', 1)[1]
                        for line in lines
                        if line.lower().startswith(b'proxy-authorization: ')
                    )
                    body = b'{"results": []}'
                    conn.sendall(
                        b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n'
                        + f'Content-Length: {len(body)}\r\n'.encode()
                        + b'Connection: close\r\n\r\n'
                        + body
                    )
            except Exception as exc:
                server_errors.append(exc)
            finally:
                listener.close()

        thread = threading.Thread(target=serve_proxy, daemon=True)
        thread.start()
        try:
            client = mediaRenamer.TMDbClient(
                api_key='api-secret',
                api_base_url='http://tmdb.test',
                proxy={'url': f'http://:only-secret@127.0.0.1:{proxy_port}'},
            )
            https_proxy_manager = client.session.get_adapter('https://').proxy_manager_for(
                client.proxy_url)
            result = client.request('configuration')
        finally:
            thread.join(timeout=3)

        self.assertFalse(thread.is_alive())
        self.assertEqual([], server_errors)
        self.assertEqual({'results': []}, result)
        self.assertEqual(
            {'Proxy-Authorization': 'Basic Om9ubHktc2VjcmV0'},
            https_proxy_manager.proxy_headers,
        )
        self.assertEqual(b'Basic Om9ubHktc2VjcmV0', captured['authorization'])
        self.assertEqual(
            b'GET http://tmdb.test/3/configuration?language=zh-CN&api_key=api-secret HTTP/1.1',
            captured['requestLine'],
        )

    def test_tmdb_request_errors_redact_api_and_proxy_credentials(self):
        proxy = {'url': 'socks://proxy-user:p%40ss%2Fword@proxy.local:1080'}
        encoded_password = 'p%40ss%2Fword'
        proxy_url = f'socks5h://proxy-user:{encoded_password}@proxy.local:1080'
        secret_text = (
            'failed https://api.example/3/search/movie?api_key=api-secret '
            f'with bearer-secret via {proxy_url}'
        )
        failures = [
            mediaRenamer.requests.ConnectionError(secret_text),
            mock.Mock(status_code=502, text=secret_text),
        ]

        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                session = mock.Mock()
                if isinstance(failure, Exception):
                    session.get.side_effect = failure
                else:
                    session.get.return_value = failure
                client = mediaRenamer.TMDbClient(
                    api_key='api-secret',
                    bearer_token='bearer-secret',
                    proxy=proxy,
                    session=session,
                )

                with self.assertRaises(mediaRenamer.TMDbError) as caught:
                    client.request('search/movie', {'query': 'Dune'})

                message = str(caught.exception)
                self.assertIn('<redacted>', message)
                for secret in (
                        'api-secret',
                        'bearer-secret',
                        'p@ss/word',
                        encoded_password,
                        proxy_url):
                    self.assertNotIn(secret, message)


class MediaSingleFileTests(unittest.TestCase):
    def setUp(self):
        LNG.set_context_lang('en')

    def test_single_file_rule_preserves_type_and_disables_recursive(self):
        config = mediaScrapingService._normalize_config({
            'rules': [{
                'path': '/115/incoming/Movie.2025.mkv',
                'type': 'tv',
                'recursive': True,
                'singleFile': True,
            }],
        })
        rule = config['rules'][0]
        self.assertEqual('tv', rule['type'])
        self.assertFalse(rule['recursive'])
        self.assertTrue(rule['singleFile'])

    def test_single_file_preview_preserves_media_type_without_scanning_siblings(self):
        config_data = mediaScrapingService._default_config()
        config_data.update({
            'defaultOpenlistId': 1,
            'openlistIds': [1],
        })
        openlist = {
            'id': 1,
            'remark': 'test',
            'url': 'http://openlist.test',
            'token': 'token',
        }
        cases = [
            (
                '/115/临时转存/Sinners.2025.2160p.WEB-DL.H265.mkv',
                'movie',
                ('Sinners', '2025'),
                '/115/临时转存/Sinners (2025)/',
                'movie',
            ),
            (
                '/115/最近接收/罪人 (2025)/罪人.2025.2160p.WEB-DL.H265.mkv',
                'movie',
                ('罪人', '2025'),
                '/115/最近接收/罪人 (2025)/',
                'movie',
            ),
            (
                '/115/临时转存/Slow.Horses.2022.S03E01.2160p.WEB-DL.H265.mkv',
                'auto',
                ('Slow Horses', '2022'),
                '/115/临时转存/Slow Horses (2022)/Season 3/',
                'tv',
            ),
        ]
        for source_path, requested_type, resolved, target_prefix, detected_type in cases:
            client = mock.Mock()
            tmdb_client = mock.Mock()
            tmdb_client.enabled.return_value = True
            tmdb_client.resolve.return_value = resolved
            with self.subTest(requested_type=requested_type), \
                    mock.patch.object(mediaScrapingService.openlistMapper, 'getOpenlistById', return_value=openlist), \
                    mock.patch.object(mediaScrapingService, 'build_client', return_value=client), \
                    mock.patch.object(mediaScrapingService, 'build_tmdb_client', return_value=tmdb_client), \
                    mock.patch.object(mediaScrapingService, 'collect_files') as collect_mock:
                result = mediaScrapingService.previewNaming({
                    'openlistId': 1,
                    'path': source_path,
                    'type': requested_type,
                    'recursive': True,
                    'singleFile': True,
                    'config': config_data,
                })

            client.login.assert_called_once_with()
            collect_mock.assert_not_called()
            self.assertEqual(requested_type, result['type'])
            self.assertFalse(result['recursive'])
            self.assertTrue(result['singleFile'])
            self.assertEqual(1, result['total'])
            self.assertEqual(source_path, result['items'][0]['srcPath'])
            self.assertTrue(result['items'][0]['targetPath'].startswith(target_prefix))
            if '/罪人 (2025)/' in source_path:
                self.assertEqual(1, result['items'][0]['targetPath'].count('/罪人 (2025)'))
            self.assertEqual([], result['rootRenames'])
            self.assertEqual(detected_type, tmdb_client.resolve.call_args.args[0])

    def test_single_movie_rerun_uses_source_or_target_file(self):
        source_path = '/115/incoming/Movie.2025.mkv'
        target_path = '/115/incoming/Movie (2025)/Movie.2025.mkv'
        request = {
            'path': source_path,
            'type': 'movie',
            'recursive': False,
            'singleFile': True,
            'plans': [{
                'srcPath': source_path,
                'targetPath': target_path,
            }],
            'config': {
                'rules': [{
                    'path': source_path,
                    'type': 'movie',
                    'recursive': False,
                    'singleFile': True,
                }],
            },
        }

        with mock.patch.object(mediaScrapingService, '_refresh_openlist_paths'), \
                mock.patch.object(mediaScrapingService, '_openlist_path_exists', side_effect=[True, False]):
            source_request = mediaScrapingService._prepare_rerun_request(request, openlist_id=1)
        self.assertEqual(source_path, source_request['path'])
        self.assertTrue(source_request['singleFile'])
        self.assertTrue(source_request['config']['rules'][0]['singleFile'])

        with mock.patch.object(mediaScrapingService, '_refresh_openlist_paths'), \
                mock.patch.object(mediaScrapingService, '_openlist_path_exists', side_effect=[False, True]):
            target_request = mediaScrapingService._prepare_rerun_request(request, openlist_id=1)
        self.assertEqual(target_path, target_request['path'])
        self.assertTrue(target_request['singleFile'])
        self.assertFalse(target_request['recursive'])
        self.assertTrue(target_request['config']['rules'][0]['singleFile'])
        self.assertFalse(target_request['config']['rules'][0]['recursive'])

    def test_single_file_rerun_without_target_does_not_refresh_root(self):
        source_path = '/115/incoming/Episode.S01E01.mkv'
        request = {
            'path': source_path,
            'type': 'tv',
            'recursive': False,
            'singleFile': True,
            'plans': [{'srcPath': source_path}],
            'config': {
                'rules': [{
                    'path': source_path,
                    'type': 'tv',
                    'recursive': False,
                    'singleFile': True,
                }],
            },
        }

        with mock.patch.object(mediaScrapingService, '_refresh_openlist_paths') as refresh_mock, \
                mock.patch.object(mediaScrapingService, '_openlist_path_exists', return_value=True):
            rerun_request = mediaScrapingService._prepare_rerun_request(request, openlist_id=1)

        self.assertEqual(source_path, rerun_request['path'])
        self.assertEqual((1, ['/115/incoming']), refresh_mock.call_args.args)
        self.assertNotIn('/', refresh_mock.call_args.args[1])


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload


class NotificationTests(unittest.TestCase):
    def setUp(self):
        LNG.set_context_lang('en')

    def test_notification_validation_rejects_missing_secret(self):
        notify = {'method': 3, 'params': json.dumps({'corpid': 'corp', 'agentid': 'agent'})}
        with self.assertRaisesRegex(Exception, 'incomplete'):
            notifyService.validateNotify(notify)

    def test_wecom_validation_accepts_numeric_agent_id(self):
        notify = {'method': 3, 'params': json.dumps({
            'corpid': 'corp', 'agentid': 1000002, 'corpsecret': 'secret'})}
        params = notifyService.validateNotify(notify)
        self.assertEqual(1000002, params['agentid'])

    def test_wecom_uses_parameterized_credentials(self):
        notify = {'method': 3, 'params': json.dumps({
            'corpid': 'corp-id', 'agentid': 'agent-id', 'corpsecret': 'private-secret', 'touser': '@all'})}
        with mock.patch.object(notifyService.requests, 'get', return_value=FakeResponse({
                'errcode': 0, 'access_token': 'access-token'})) as get_mock, mock.patch.object(
                notifyService.requests, 'post', return_value=FakeResponse({'errcode': 0})) as post_mock:
            notifyService.sendNotify(notify, 'Title', 'Content')
        self.assertNotIn('private-secret', get_mock.call_args.args[0])
        self.assertEqual('private-secret', get_mock.call_args.kwargs['params']['corpsecret'])
        self.assertNotIn('access-token', post_mock.call_args.args[0])
        self.assertEqual('access-token', post_mock.call_args.kwargs['params']['access_token'])
        self.assertEqual('agent-id', post_mock.call_args.kwargs['json']['agentid'])

    def test_notification_network_error_does_not_expose_secret(self):
        notify = {'method': 3, 'params': json.dumps({
            'corpid': 'corp-id', 'agentid': 'agent-id', 'corpsecret': 'private-secret'})}
        with mock.patch.object(notifyService.requests, 'get', side_effect=notifyService.requests.ConnectionError(
                'request failed for private-secret')):
            with self.assertRaises(Exception) as raised:
                notifyService.sendNotify(notify, 'Title', 'Content')
        self.assertNotIn('private-secret', str(raised.exception))

    def test_lark_interactive_card(self):
        notify = {'method': 4, 'params': json.dumps({'url': 'https://open.larksuite.test/hook/token'})}
        with mock.patch.object(notifyService.requests, 'post', return_value=FakeResponse({'code': 0})) as post_mock:
            notifyService.sendNotify(notify, 'Title', '**Content**')
        payload = post_mock.call_args.kwargs['json']
        self.assertEqual('interactive', payload['msg_type'])
        self.assertEqual('Title', payload['card']['header']['title']['content'])
        self.assertEqual('**Content**', payload['card']['elements'][0]['content'])

    def test_media_notification_uses_request_language(self):
        LNG.set_context_lang('en')
        task = {
            'taskName': 'Modern Family (2009)',
            'openlistName': 'Primary OpenList',
            'path': '/115/Modern Family (2009)',
            'status': 2,
            'total': 3,
            'successNum': 2,
            'skipNum': 1,
            'failNum': 0,
            'elapsed': 5,
        }
        with mock.patch.object(mediaScrapingService.notifyService, 'getNotifyList', return_value=[{'id': 1}]), \
                mock.patch.object(mediaScrapingService.notifyService, 'sendNotify') as send_mock:
            mediaScrapingService._send_task_notify(task)
        title, content = send_mock.call_args.args[1:3]
        self.assertEqual('Media renaming success - OpenListSync', title)
        self.assertIn('Task: Modern Family (2009)', content)
        self.assertIn('3 rename items: 2 succeeded, 1 skipped, and 0 failed.', content)

    def test_media_background_task_inherits_request_language(self):
        LNG.set_context_lang('zh-CN')
        observed = []
        result = {'success': True, 'results': [{}]}
        task = {'status': 2}

        with mock.patch.object(
                mediaScrapingService, '_prepare_task_preview_items', side_effect=lambda _task_id, req, _config: req), \
                mock.patch.object(mediaScrapingService, 'runScraping', return_value=result), \
                mock.patch.object(mediaScrapingService, '_update_run_task', return_value=task), \
                mock.patch.object(
                    mediaScrapingService,
                    '_send_task_notify',
                    side_effect=lambda _task: observed.append(LNG.G('success'))), \
                mock.patch.object(mediaScrapingService, '_log_run_result'):
            mediaScrapingService._run_task_background(
                1,
                {'path': '/115/test', 'config': {}},
                request_lang='en-US',
            )

        self.assertEqual(['Success'], observed)

    def test_media_reruns_forward_current_request_language(self):
        task = {
            'id': 1,
            'jobId': None,
            'path': '/115/test',
            'openlistId': 2,
            'request': json.dumps({'path': '/115/test', 'config': {}}),
            'rootRenames': '[]',
        }
        job = {
            'id': 3,
            'path': '/115/test',
            'openlistId': 2,
            'request': json.dumps({'path': '/115/test', 'config': {}}),
        }

        with mock.patch.object(mediaScrapingService.mediaScrapingMapper, 'getTaskById', return_value=task), \
                mock.patch.object(mediaScrapingService.mediaScrapingMapper, 'getJobById', return_value=job), \
                mock.patch.object(mediaScrapingService, '_ensure_legacy_jobs'), \
                mock.patch.object(mediaScrapingService, '_latest_task_with_root_rename_hints', return_value=None), \
                mock.patch.object(mediaScrapingService.mediaScrapingMapper, 'getLatestTaskByJobId', return_value=task), \
                mock.patch.object(
                    mediaScrapingService,
                    '_prepare_rerun_request',
                    side_effect=lambda task_req, *_args: task_req), \
                mock.patch.object(mediaScrapingService, 'startRunTask', return_value={}) as start_mock:
            mediaScrapingService.rerunTask({'taskId': 1, '__lang': 'en-US'})
            mediaScrapingService.rerunJob({'jobId': 3, '__lang': 'en-US'})

        self.assertEqual('en-US', start_mock.call_args_list[0].args[0]['__lang'])
        self.assertEqual('en-US', start_mock.call_args_list[1].args[0]['__lang'])

    def test_webhook_api_key_mismatch_is_redacted_from_logs(self):
        logger = logging.getLogger()
        with mock.patch.dict(os.environ, {'WEBHOOK_APIKEY': 'expected-secret'}, clear=True), \
                mock.patch.object(logger, 'warning') as warning:
            result = webhookService.handleWebhook({'apikey': 'provided-secret'})
        self.assertEqual('ignored: apikey mismatch', result['job'])
        message = warning.call_args.args[0]
        self.assertNotIn('expected-secret', message)
        self.assertNotIn('provided-secret', message)

    def test_webhook_without_openlist_sends_localized_notification(self):
        class ImmediateTimer:
            def __init__(self, delay, callback):
                self.callback = callback

            def start(self):
                self.callback()

        with mock.patch.dict(os.environ, {'WEBHOOK_DELAY': '0'}, clear=True), \
                mock.patch.object(webhookService.threading, 'Timer', ImmediateTimer), \
                mock.patch('mapper.jobMapper.getJobList', return_value=[]), \
                mock.patch('mapper.openlistMapper.getOpenlistList', return_value=[]), \
                mock.patch.object(webhookService.notifyService, 'getNotifyList', return_value=[{'id': 1}]), \
                mock.patch.object(webhookService.notifyService, 'sendNotify') as send_mock:
            webhookService.handleWebhook({'title': 'Modern Family (2009) 已入库'})
        self.assertEqual('Webhook received, but no engine is configured', send_mock.call_args.args[1])
        self.assertIn('Add an OpenList URL', send_mock.call_args.args[2])

    def test_webhook_checks_exact_source_and_dst_paths(self):
        class ImmediateTimer:
            def __init__(self, delay, callback):
                self.callback = callback

            def start(self):
                self.callback()

        remark = 'Modern Family (2009)'
        source_path = f'/media/tv/comedy/{remark}'
        dst_path = f'/archive/tv/comedy/{remark}'
        client = mock.Mock()
        client.pathExists.side_effect = lambda path, is_dir: is_dir and path in {
            source_path,
            dst_path,
        }
        created_job = {'id': 67, 'remark': remark, 'openlistId': 1}
        env = {
            'WEBHOOK_DELAY': '0',
            'WEBHOOK_OPENLIST_NAME': 'OpenList',
            'TVsource': '/media/tv',
            'MOVsource': '/media/movie',
            'SECOND': 'true',
            'DST_TV_TARGETS': '/archive/tv',
            'SYNC_TV_TARGETS': '/fallback/tv',
        }

        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(webhookService.threading, 'Timer', ImmediateTimer), \
                mock.patch('mapper.jobMapper.getJobList', side_effect=[[], [created_job]]), \
                mock.patch('mapper.openlistMapper.getOpenlistList', return_value=[{
                    'id': 1,
                    'remark': 'OpenList',
                }]), \
                mock.patch('service.openlist.openlistService.getClientById', return_value=client), \
                mock.patch('service.syncJob.jobService.addJobClient') as add_mock, \
                mock.patch('service.syncJob.jobService.doJobManual') as run_mock:
            result = webhookService.handleWebhook({
                'title': f'{remark} S01 E01 已入库',
                'text': '类型：电视剧，类别：comedy',
            })

        self.assertEqual({'remark': remark, 'scheduled_after_sec': 0}, result['job'])
        self.assertEqual([
            mock.call(source_path, True),
            mock.call(dst_path, True),
        ], client.pathExists.call_args_list)
        client.filePathList.assert_not_called()
        payload = add_mock.call_args.args[0]
        self.assertEqual(source_path + '/', payload['srcPath'])
        self.assertEqual(dst_path + '/', payload['dstPath'])
        run_mock.assert_called_once_with(67)

    def test_refresh_deduplicates_before_openlist_calls(self):
        refreshService._recent_refresh.clear()
        refreshService._recent_refresh['stale'] = 1
        client = mock.Mock()
        client.fileListApi.return_value = {}
        job = {
            'openlistId': 1,
            'remark': 'Modern Family (2009)',
            'srcPath': '/source/Modern Family (2009)/',
            'dstPath': '/target/Modern Family (2009)/',
        }
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(refreshService.openlistService, 'getClientById', return_value=client), \
                mock.patch.object(refreshService.notifyService, 'getNotifyList', return_value=[{'id': 1}]), \
                mock.patch.object(refreshService.notifyService, 'sendNotify') as send_mock:
            refreshService.refresh_after_task(job, 2)
            refreshService.refresh_after_task(job, 2)
            refreshService.refresh_after_task({
                **job,
                'srcPath': '/other/Modern Family (2009)/',
                'dstPath': '/other-target/Modern Family (2009)/',
            }, 2)
        self.assertEqual(2, client.fileListApi.call_count)
        self.assertEqual('Directory refresh completed', send_mock.call_args.args[1])
        self.assertNotIn('stale', refreshService._recent_refresh)
        refreshService._recent_refresh.clear()


if __name__ == '__main__':
    unittest.main()
