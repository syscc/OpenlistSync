import request from "@/utils/request";

const mediaRequest = (method, data, timeout) =>
  request({
    url: "/media/scraping",
    method,
    headers: { isMask: false },
    ...(timeout ? { timeout } : {}),
    ...(data ? { data } : {}),
  });

const mediaAction = (action, data = {}, timeout) =>
  mediaRequest("put", { ...data, action }, timeout);

export function getMediaScrapingConfig() {
  return mediaRequest("get");
}

export function saveMediaScrapingConfig(data) {
  return mediaRequest("post", data);
}

export function runMediaScraping(data) {
  return mediaRequest("put", data, 30 * 60 * 1000);
}

export function browseMediaScraping(data) {
  return mediaAction("browse", data);
}

export function previewMediaScraping(data) {
  return mediaAction("preview", data, 30 * 60 * 1000);
}

export function searchMediaTmdb(data) {
  return mediaAction("tmdbSearch", data);
}

export function getMediaScrapingTasks(data) {
  return mediaAction("taskList", data);
}

export function getMediaScrapingTaskItems(data) {
  return mediaAction("taskItems", data);
}

export function getMediaScrapingJobTasks(data) {
  return mediaAction("jobTasks", data);
}

export function getMediaScrapingJobCurrent(data) {
  return mediaAction("jobCurrent", data);
}

export function deleteMediaScrapingJob(jobId) {
  return mediaAction("deleteJob", { jobId });
}

export function deleteMediaScrapingTask(taskId) {
  return mediaAction("deleteTask", { taskId });
}

export function rerunMediaScrapingJob(jobId) {
  return mediaAction("rerunJob", { jobId });
}

export function abortMediaScrapingJob(jobId) {
  return mediaAction("abortJob", { jobId });
}

export function abortMediaScrapingTask(taskId) {
  return mediaAction("abortTask", { taskId });
}

export function rerunMediaScrapingTask(taskId) {
  return mediaAction("rerunTask", { taskId });
}
