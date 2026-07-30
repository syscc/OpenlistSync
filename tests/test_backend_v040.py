import hashlib
import json
import logging
import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from common import LNG, config, locales, sqlInit
from data import start as sourceStart
from service.mediaScraping import mediaScrapingService
from service.notify import notifyService
from service.syncJob import jobClient, jobService, taskService
from service.system import onStart
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
