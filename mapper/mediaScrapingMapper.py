from common import sqlBase


def addTask(task):
    return sqlBase.execute_insert(
        "insert into media_scraping_task (jobId, taskName, path, openlistId, openlistName, status, apply, usedPreviewPlans, "
        "total, changed, successNum, failNum, skipNum, elapsed, rootRenames, stdout, stderr, errMsg, request, updateTime) "
        "VALUES (:jobId, :taskName, :path, :openlistId, :openlistName, :status, :apply, :usedPreviewPlans, :total, :changed, "
        ":successNum, :failNum, :skipNum, :elapsed, :rootRenames, :stdout, :stderr, :errMsg, :request, :updateTime)",
        task,
    )


def addTaskItems(items):
    if not items:
        return
    sqlBase.execute_manny(
        "insert into media_scraping_task_item (taskId, srcPath, targetPath, status, title, year, season, episode, errMsg) "
        "VALUES (:taskId, :srcPath, :targetPath, :status, :title, :year, :season, :episode, :errMsg)",
        items,
    )


def addJob(job):
    return sqlBase.execute_insert(
        "insert into media_scraping_job (groupKey, taskName, path, openlistId, openlistName, request, latestTaskId, "
        "status, total, changed, successNum, failNum, skipNum, elapsed, updateTime) "
        "VALUES (:groupKey, :taskName, :path, :openlistId, :openlistName, :request, :latestTaskId, :status, "
        ":total, :changed, :successNum, :failNum, :skipNum, :elapsed, :updateTime)",
        job,
    )


def getJobById(job_id):
    rst = sqlBase.fetchall_to_table("select * from media_scraping_job where id=?", (job_id,))
    return rst[0] if rst else None


def getJobByGroupKey(group_key):
    rst = sqlBase.fetchall_to_table("select * from media_scraping_job where groupKey=?", (group_key,))
    return rst[0] if rst else None


def getJobs(req):
    return sqlBase.fetchall_to_page(
        "select * from media_scraping_job order by updateTime desc, createTime desc, id desc ",
        req,
    )


def updateJob(job):
    sqlBase.execute_update(
        "update media_scraping_job set groupKey=:groupKey, taskName=:taskName, path=:path, openlistId=:openlistId, "
        "openlistName=:openlistName, request=:request, latestTaskId=:latestTaskId, status=:status, total=:total, "
        "changed=:changed, successNum=:successNum, failNum=:failNum, skipNum=:skipNum, elapsed=:elapsed, "
        "updateTime=:updateTime where id=:id",
        job,
    )


def updateTaskJobId(task_id, job_id):
    sqlBase.execute_update("update media_scraping_task set jobId=? where id=?", (job_id, task_id))


def countTasksByJobId(job_id):
    rst = sqlBase.fetchall_to_table("select count(id) as num from media_scraping_task where jobId=?", (job_id,))
    return rst[0]['num'] if rst else 0


def deleteJobOnly(job_id):
    sqlBase.execute_update("delete from media_scraping_job where id=?", (job_id,))


def getTasksWithoutJob():
    return sqlBase.fetchall_to_table(
        "select * from media_scraping_task where jobId is null or jobId=0 order by createTime asc, id asc"
    )


def getTaskList(req):
    return sqlBase.fetchall_to_page(
        "select * from media_scraping_task where jobId=:jobId order by createTime desc, id desc ",
        req,
    )


def getAllTaskList(req):
    return sqlBase.fetchall_to_page(
        "select * from media_scraping_task order by createTime desc, id desc ",
        req,
    )


def getTaskItems(req):
    type_filter = req.get('type')
    type_sql = ''
    if type_filter is not None and type_filter != '':
        try:
            type_filter = int(type_filter)
        except (TypeError, ValueError):
            type_filter = None
        if type_filter is not None:
            if type_filter == 0:
                type_sql = "and status not in (3,7) and srcPath != targetPath "
            elif type_filter == 3:
                type_sql = "and status=3 "
            elif type_filter == 7:
                type_sql = "and status=7 "
    return sqlBase.fetchall_to_page(
        "select * from media_scraping_task_item where taskId=:taskId "
        f"{'and status=:status ' if 'status' in req and req.get('status') is not None else ''}"
        f"{type_sql}"
        "order by id asc ",
        req,
    )


def getTaskById(task_id):
    rst = sqlBase.fetchall_to_table("select * from media_scraping_task where id=?", (task_id,))
    return rst[0] if rst else None


def getTaskItemStats(task_id):
    rows = sqlBase.fetchall_to_table(
        "select status, count(id) as num from media_scraping_task_item where taskId=? group by status",
        (task_id,),
    )
    return {item['status']: item['num'] for item in rows}


def updateTask(task):
    sqlBase.execute_update(
        "update media_scraping_task set jobId=:jobId, taskName=:taskName, path=:path, openlistId=:openlistId, "
        "openlistName=:openlistName, status=:status, apply=:apply, usedPreviewPlans=:usedPreviewPlans, "
        "total=:total, changed=:changed, successNum=:successNum, failNum=:failNum, skipNum=:skipNum, "
        "elapsed=:elapsed, rootRenames=:rootRenames, stdout=:stdout, stderr=:stderr, errMsg=:errMsg, "
        "request=:request, updateTime=:updateTime where id=:id",
        task,
    )


def updateTaskStatus(task_id, status, err_msg=''):
    sqlBase.execute_update(
        "update media_scraping_task set status=?, errMsg=?, updateTime=strftime('%s', 'now') where id=?",
        (status, err_msg, task_id),
    )


def updateTaskItemsStatus(task_id, status):
    sqlBase.execute_update(
        "update media_scraping_task_item set status=? where taskId=? and status in (0,1)",
        (status, task_id),
    )


def updateTaskItemStatus(task_id, src_path, status, err_msg='', target_path=None):
    if target_path is None:
        sqlBase.execute_update(
            "update media_scraping_task_item set status=?, errMsg=? where taskId=? and srcPath=? and status in (0,1)",
            (status, err_msg, task_id, src_path),
        )
    else:
        sqlBase.execute_update(
            "update media_scraping_task_item set status=?, errMsg=? where taskId=? and srcPath=? and targetPath=? and status in (0,1)",
            (status, err_msg, task_id, src_path, target_path),
        )


def deleteTaskItems(task_id):
    sqlBase.execute_update("delete from media_scraping_task_item where taskId=?", (task_id,))


def deleteTask(task_id):
    sqlBase.execute_update("delete from media_scraping_task_item where taskId=?", (task_id,))
    sqlBase.execute_update("delete from media_scraping_task where id=?", (task_id,))


def deleteJob(job_id):
    task_ids = sqlBase.fetchall_to_table("select id from media_scraping_task where jobId=?", (job_id,))
    for item in task_ids:
        sqlBase.execute_update("delete from media_scraping_task_item where taskId=?", (item['id'],))
    sqlBase.execute_update("delete from media_scraping_task where jobId=?", (job_id,))
    sqlBase.execute_update("delete from media_scraping_job where id=?", (job_id,))


def getRunningTaskByJobId(job_id):
    rst = sqlBase.fetchall_to_table(
        "select * from media_scraping_task where jobId=? and status=1 order by createTime desc, id desc limit 1",
        (job_id,),
    )
    return rst[0] if rst else None


def getLatestTaskByJobId(job_id):
    rst = sqlBase.fetchall_to_table(
        "select * from media_scraping_task where jobId=? order by createTime desc, id desc limit 1",
        (job_id,),
    )
    return rst[0] if rst else None


def getLatestTaskWithRootRenamesByJobId(job_id):
    rst = sqlBase.fetchall_to_table(
        "select * from media_scraping_task where jobId=? and rootRenames is not null "
        "and rootRenames!='' and rootRenames!='[]' order by createTime desc, id desc limit 1",
        (job_id,),
    )
    return rst[0] if rst else None


def pruneTasks(limit):
    if limit <= 0:
        return
    old_tasks = sqlBase.fetchall_to_table(
        "select id from media_scraping_task order by createTime desc, id desc limit -1 offset ?",
        (limit,),
    )
    for item in old_tasks:
        deleteTask(item['id'])
