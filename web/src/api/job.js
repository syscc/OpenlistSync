import request from "@/utils/request";

export function openlistGet() {
  return request({
    url: "/openlist",
    headers: { isMask: false },
    method: "get",
  });
}

export function openlistGetPath(openlistId, path) {
  return request({
    url: "/openlist",
    headers: { isMask: false },
    method: "get",
    params: {
      openlistId,
      path,
    },
  });
}

export function openlistMkdir(data) {
  return request({
    url: "/openlist",
    headers: { isMask: false },
    method: "post",
    data: {
      ...data,
      action: "mkdir",
    },
  });
}

export function openlistPost(data) {
  return request({
    url: "/openlist",
    headers: { isMask: false },
    method: "post",
    data,
  });
}

export function openlistPut(data) {
  return request({
    url: "/openlist",
    headers: { isMask: false },
    method: "put",
    data,
  });
}

export function openlistDelete(id) {
  return request({
    url: "/openlist",
    headers: { isMask: false },
    method: "delete",
    data: { id },
  });
}

export function jobPost(data) {
  return request({
    url: "/job",
    headers: { isMask: false },
    method: "post",
    data,
  });
}

export function jobGetJob(params) {
  return request({
    url: "/job",
    headers: { isMask: false },
    method: "get",
    params,
  });
}

export function jobPut(data) {
  return request({
    url: "/job",
    headers: { isMask: false },
    method: "put",
    data,
  });
}

export function jobDelete(data) {
  return request({
    url: "/job",
    headers: { isMask: false },
    method: "delete",
    data,
  });
}

export function jobGetTaskCurrent(data) {
  return request({
    url: "/job",
    headers: { isMask: false },
    method: "get",
    params: {
      ...data,
      current: 1,
    },
  });
}

export function jobGetTask(params) {
  return request({
    url: "/job",
    headers: { isMask: false },
    method: "get",
    params,
  });
}

export function jobDeleteTask(taskId) {
  return request({
    url: "/job",
    headers: { isMask: false },
    method: "delete",
    data: { taskId },
  });
}

export function jobGetTaskItem(params) {
  return request({
    url: "/job",
    headers: { isMask: false },
    method: "get",
    params,
  });
}
