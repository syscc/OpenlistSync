import request from "@/utils/request";

export function getSystemConfig() {
  return request({
    url: "/system/config",
    method: "get",
    headers: { isMask: false },
  });
}

export function saveSystemConfig(data) {
  return request({
    url: "/system/config",
    method: "post",
    headers: { isMask: false },
    data,
  });
}

export function saveLanguage(language) {
  return request({
    url: "/language",
    method: "post",
    headers: { isMask: false },
    data: { language },
  });
}
