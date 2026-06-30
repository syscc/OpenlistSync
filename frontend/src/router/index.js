import Vue from 'vue'
import VueRouter from 'vue-router'
import Layout from '@/views/layout.vue'

const originalPush = VueRouter.prototype.push

VueRouter.prototype.push = function push(location) {
  return originalPush.call(this, location).catch(err => err)
}

Vue.use(VueRouter)

const routes = [{
		path: '/',
		name: '首页',
		meta: {
			disableLeft: true,
			letfIndex: ''
		},
		component: () => import('@/views/index')
	},
	{
		path: '/login',
		name: '登录',
		meta: {
			disableLeft: true,
			letfIndex: ''
		},
		component: () => import('@/views/Login')
	},
	{
		path: '/home',
		component: Layout,
		children: [{
			path: '',
			component: () => import('@/views/page/home/index'),
			name: '作业管理',
			meta: {
				letfIndex: '/home'
			}
		},{
			path: 'task',
			component: () => import('@/views/page/home/task'),
			name: '任务列表',
			meta: {
				letfIndex: '/home'
			}
		},{
			path: 'task/detail',
			component: () => import('@/views/page/home/taskDetail'),
			name: '任务详情',
			meta: {
				letfIndex: '/home'
			}
		}]
	},
	{
		path: '/mediaScraping',
		component: Layout,
		children: [{
			path: '',
			component: () => import('@/views/page/mediaScraping/index'),
			name: '媒体名字刮削',
			meta: {
				letfIndex: '/mediaScraping'
			}
		},{
			path: 'task/detail',
			component: () => import('@/views/page/mediaScraping/taskDetail'),
			name: '媒体刮削任务详情',
			meta: {
				letfIndex: '/mediaScraping'
			}
		},{
			path: 'task/item',
			component: () => import('@/views/page/mediaScraping/taskItemDetail'),
			name: '媒体刮削执行详情',
			meta: {
				letfIndex: '/mediaScraping'
			}
		}]
	},
	{
		path: '/engine',
		component: Layout,
		children: [{
			path: '',
			component: () => import('@/views/page/engine/index'),
			name: '引擎管理',
			meta: {
				letfIndex: '/engine'
			}
		}]
	},
	{
		path: '/notify',
		component: Layout,
		children: [{
			path: '',
			component: () => import('@/views/page/notify/index'),
			name: '通知配置',
			meta: {
				letfIndex: '/notify'
			}
		}]
	},
	{
		path: '/setting',
		component: Layout,
		children: [{
			path: '',
			component: () => import('@/views/page/setting/index'),
			name: '系统设置',
			meta: {
				letfIndex: '/setting'
			}
		}]
	},
	{
		path: '/globalExclude',
		component: Layout,
		children: [{
			path: '',
			component: () => import('@/views/page/globalExclude/index'),
			name: '全局排除项',
			meta: {
				letfIndex: '/globalExclude'
			}
		}]
	}
]

const router = new VueRouter({
	mode: 'hash',
	routes
})

export default router
