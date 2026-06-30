import request from '@/utils/request'


export function getMediaScrapingConfig() {
	return request({
		url: '/media/scraping',
		method: 'get'
	})
}


export function saveMediaScrapingConfig(data) {
	return request({
		url: '/media/scraping',
		method: 'post',
		data
	})
}


export function runMediaScraping(data) {
	return request({
		url: '/media/scraping',
		method: 'put',
		timeout: 30 * 60 * 1000,
		data
	})
}


export function browseMediaScraping(data) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			...data,
			action: 'browse'
		}
	})
}


export function previewMediaScraping(data) {
	return request({
		url: '/media/scraping',
		method: 'put',
		timeout: 30 * 60 * 1000,
		data: {
			...data,
			action: 'preview'
		}
	})
}


export function searchMediaTmdb(data) {
	return request({
		url: '/media/scraping',
		method: 'put',
		headers: {
			isMask: false
		},
		data: {
			...data,
			action: 'tmdbSearch'
		}
	})
}


export function getMediaScrapingTasks(data) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			...data,
			action: 'taskList'
		}
	})
}


export function getMediaScrapingTaskItems(data) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			...data,
			action: 'taskItems'
		}
	})
}


export function getMediaScrapingJobTasks(data) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			...data,
			action: 'jobTasks'
		}
	})
}


export function getMediaScrapingJobCurrent(data) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			...data,
			action: 'jobCurrent'
		}
	})
}


export function deleteMediaScrapingJob(jobId) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			action: 'deleteJob',
			jobId
		}
	})
}


export function deleteMediaScrapingTask(taskId) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			action: 'deleteTask',
			taskId
		}
	})
}


export function rerunMediaScrapingJob(jobId) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			action: 'rerunJob',
			jobId
		}
	})
}


export function abortMediaScrapingJob(jobId) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			action: 'abortJob',
			jobId
		}
	})
}


export function abortMediaScrapingTask(taskId) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			action: 'abortTask',
			taskId
		}
	})
}


export function rerunMediaScrapingTask(taskId) {
	return request({
		url: '/media/scraping',
		method: 'put',
		data: {
			action: 'rerunTask',
			taskId
		}
	})
}
