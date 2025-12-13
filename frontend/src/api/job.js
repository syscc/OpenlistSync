import request from '@/utils/request'

// openlist列表
export function openlistGet() {
	return request({
		url: '/openlist',
		headers: {
			isMask: false
		},
		method: 'get'
	})
}

// openlist子目录
export function openlistGetPath(openlistId, path) {
	return request({
		url: '/openlist',
		headers: {
			isMask: false
		},
		method: 'get',
		params: {
			openlistId,
			path
		}
	})
}

// openlist新建文件夹
export function openlistMkdir(data) {
	return request({
		url: '/openlist',
		headers: {
			isMask: false
		},
		method: 'post',
		data: {
			...data,
			action: 'mkdir'
		}
	})
}

// openlist新增
export function openlistPost(data) {
	return request({
		url: '/openlist',
		headers: {
			isMask: false
		},
		method: 'post',
		data
	})
}

// openlist修改
export function openlistPut(data) {
	return request({
		url: '/openlist',
		headers: {
			isMask: false
		},
		method: 'put',
		data
	})
}

// 删除openlist
export function openlistDelete(id) {
	return request({
		url: '/openlist',
		headers: {
			isMask: false
		},
		method: 'delete',
		data: {
			id
		}
	})
}

// 创建作业
export function jobPost(data) {
	return request({
		url: '/job',
		headers: {
			isMask: false
		},
		method: 'post',
		data
	})
}

// 作业列表
export function jobGetJob(params) {
	return request({
		url: '/job',
		headers: {
			isMask: false
		},
		method: 'get',
		params
	})
}

// 禁用/启用/手动执行/中止 作业
export function jobPut(data) {
	return request({
		url: '/job',
		headers: {
			isMask: false
		},
		method: 'put',
		data
	})
}

// 删除作业
export function jobDelete(data) {
	return request({
		url: '/job',
		headers: {
			isMask: false
		},
		method: 'delete',
		data
	})
}

// 正在执行的任务详情
export function jobGetTaskCurrent(data) {
	return request({
		url: '/job',
		headers: {
			isMask: false
		},
		method: 'get',
		params: {
			...data,
			current: 1
		}
	})
}

// 任务列表
export function jobGetTask(params) {
	return request({
		url: '/job',
		headers: {
			isMask: false
		},
		method: 'get',
		params
	})
}

// 删除任务
export function jobDeleteTask(taskId) {
	return request({
		url: '/job',
		headers: {
			isMask: false
		},
		method: 'delete',
		data: {
			taskId
		}
	})
}

// 任务详情列表
export function jobGetTaskItem(params) {
	return request({
		url: '/job',
		headers: {
			isMask: false
		},
		method: 'get',
		params
	})
}