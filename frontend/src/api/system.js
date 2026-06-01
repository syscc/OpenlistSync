import request from '@/utils/request'


export function getSystemConfig() {
	return request({
		url: '/system/config',
		method: 'get'
	})
}


export function saveSystemConfig(data) {
	return request({
		url: '/system/config',
		method: 'post',
		data
	})
}
