<template>
	<div class="media-task" :style="`min-height: calc(320px + ${currentHeight}px)`">
		<div class="top-box">
			<div class="top-box-left">
				<el-button type="primary" icon="el-icon-back" size="small" @click="goback">返回</el-button>
				<el-button type="primary" icon="el-icon-caret-right" size="small" @click="rerunJob"
					:loading="btnLoading">手动执行</el-button>
			</div>
			<div class="top-box-title">作业详情</div>
			<el-button size="small" icon="el-icon-refresh" :loading="loading" @click="refreshAll">刷新</el-button>
		</div>

		<div class="current-box" v-if="current" :style="`height: ${currentHeight}px;`">
			<div class="current-box-top">
				<div class="current-box-top-left">
					<div class="top-line">
						<div class="top-field">
							整体进度：
							<el-progress :stroke-width="20" :text-inside="true" style="width: 130px;"
								color="rgba(64, 158, 255, .8)" text-color="#fff"
								define-back-color="rgba(64, 158, 255, .3)"
								:percentage="Number(Number(current.summary.progress || 0).toFixed(4))"></el-progress>
						</div>
						<div>当前状态：{{taskStatusText(current.task.status)}}</div>
						<div>平均速度：{{formatSpeed(avgSpeed)}} 个/s</div>
						<div>瞬时速度：{{formatSpeed(currentSpeed)}} 个/s</div>
					</div>
					<div class="top-line">
						<div>持续时间：{{formatDuration(current.summary.elapsed)}}</div>
						<div>预计还要：{{formatRemaining(current.summary.remaining)}}</div>
						<div>开始时间：{{current.task.createTime ? (current.task.createTime | timeStampFilter) : '--'}}</div>
						<div>预计完成：{{estimatedFinishText}}</div>
					</div>
				</div>
				<div class="current-box-top-right">
					<el-button type="danger" @click="abortJob" :loading="btnLoading">中止任务</el-button>
				</div>
			</div>
			<div class="task-title-line">
				<span>{{displayTaskName(current.task)}}</span>
				<span>{{displayTaskPath(current.task)}}</span>
			</div>
			<div class="current-box-bottom">
				<div class="current-echart-box" ref="progressChart"></div>
				<div class="current-box-task">
					<div class="current-box-task-left">
						<div v-for="item in statusTabs" :key="item.status" @click="changeStatus(item.status)"
							:class="`task-left-item${currentStatus === item.status ? ' is-current' : ''}`">
							<span>{{item.label}}</span>
							<b>{{statusCount(item)}}</b>
						</div>
					</div>
					<div class="current-box-task-right">
						<el-table :data="current.taskItemList" height="calc(100% - 36px)" class="table-data"
							v-loading="currentLoading" empty-text="暂无明细">
							<el-table-column type="expand">
								<template slot-scope="props">
									<div class="detail-expand">
										<div class="expand-row">
											<span class="expand-label">来源目录</span>
											<span class="expand-value">{{sourceDir(props.row)}}</span>
										</div>
										<div class="expand-row">
											<span class="expand-label">目标目录</span>
											<span class="expand-value">{{targetDir(props.row)}}</span>
										</div>
										<div class="expand-row">
											<span class="expand-label">创建时间</span>
											<span class="expand-value">{{props.row.createTime | timeStampFilter}}</span>
										</div>
										<div class="expand-row" v-if="props.row.errMsg">
											<span class="expand-label">原因</span>
											<span class="expand-value stderr">{{reasonText(props.row)}}</span>
										</div>
									</div>
								</template>
							</el-table-column>
							<el-table-column label="文件名/目录" min-width="260">
								<template slot-scope="scope">
									<div class="path-cell">{{fileName(scope.row)}}</div>
								</template>
							</el-table-column>
							<el-table-column label="文件大小" width="120">
								<template slot-scope="scope">{{fileSize(scope.row)}}</template>
							</el-table-column>
							<el-table-column label="操作类型" width="90">
								<template slot-scope="scope">
									<div :class="`bg-status bg-${operationTypeBg(scope.row)}`" style="width: 58px;">
										{{operationTypeText(scope.row)}}
									</div>
								</template>
							</el-table-column>
							<el-table-column label="状态" width="120">
								<template slot-scope="scope">
									<el-progress :stroke-width="20" v-if="Number(scope.row.status) === 1" :text-inside="true"
										style="width: 90px;" color="rgba(64, 158, 255, .8)" text-color="#fff"
										define-back-color="rgba(64, 158, 255, .3)" :percentage="Number(itemProgress(scope.row).toFixed(3))"></el-progress>
									<div :class="`bg-status bg-${itemStatusBg(scope.row.status)}`" v-else>
										<span v-if="Number(scope.row.status) !== 7">{{taskItemStatusText(scope.row.status)}}</span>
										<el-popover v-else placement="top-end" title="错误原因" width="220" trigger="hover"
											:content="reasonText(scope.row)">
											<span slot="reference">失败，<span style="color: #409eff;">原因</span></span>
										</el-popover>
									</div>
								</template>
							</el-table-column>
						</el-table>
						<div class="page compact">
							<el-pagination small @size-change="handleCurrentSizeChange" @current-change="handleCurrentPageChange"
								:current-page="currentParams.pageNum" :page-size="currentParams.pageSize"
								:total="current.count" layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]">
							</el-pagination>
						</div>
					</div>
				</div>
			</div>
		</div>

		<div class="table-box" :style="`height: calc(100% - 117px - ${currentHeight}px);`">
			<el-table :data="taskData.taskList" height="100%" class="table-data" v-loading="loading" empty-text="暂无执行日志">
				<el-table-column type="index" label="序号" align="center" width="60"></el-table-column>
				<el-table-column label="状态" width="110">
					<template slot-scope="scope">
						<div :class="`bg-status bg-${taskStatusBg(scope.row.status)}`">
							{{taskStatusText(scope.row.status)}}
						</div>
					</template>
				</el-table-column>
				<el-table-column label="任务进度（单位个）" min-width="280">
					<template slot-scope="scope">
						<span v-if="scope.row.status == 1">执行中的任务进度见上方</span>
						<div style="display: flex;align-items: center;flex-wrap: wrap;" v-else>
							<span class="prgNum bg-8">总 {{scope.row.total || 0}}</span>
							<span class="prgNum bg-2">成 {{scope.row.successNum || 0}}</span>
							<span class="prgNum bg-7">败 {{scope.row.failNum || 0}}</span>
							<span class="prgNum bg-3">跳 {{scope.row.skipNum || 0}}</span>
						</div>
					</template>
				</el-table-column>
				<el-table-column label="耗时" width="100">
					<template slot-scope="scope">{{formatElapsed(scope.row.elapsed)}}</template>
				</el-table-column>
				<el-table-column label="创建时间" width="160">
					<template slot-scope="scope">{{scope.row.createTime | timeStampFilter}}</template>
				</el-table-column>
				<el-table-column label="操作" width="190">
					<template slot-scope="scope">
						<el-button type="danger" icon="el-icon-delete" @click="deleteTask(scope.row)"
							:loading="btnLoading" :disabled="scope.row.status == 1"
							size="mini">{{scope.row.status == 1 ? '暂不能' : ''}}删除</el-button>
						<el-button type="primary" icon="el-icon-view" @click="detail(scope.row)"
							:loading="btnLoading" size="mini" v-if="scope.row.total != 0 && Number(scope.row.status) !== 1">详情</el-button>
					</template>
				</el-table-column>
			</el-table>
		</div>
		<div class="page">
			<div class="page-tip">
				<span style="margin-right: 12px;">进度图例：</span>
				<span class="prgNum bg-8">总数</span>
				<span class="prgNum bg-2">成功</span>
				<span class="prgNum bg-3">跳过</span>
				<span class="prgNum bg-7">失败</span>
			</div>
			<el-pagination @size-change="handleSizeChange" @current-change="handleCurrentChange"
				:current-page="params.pageNum" :page-size="params.pageSize" :total="taskData.count"
				layout="total, sizes, prev, pager, next, jumper" :page-sizes="[10, 20, 50, 100]">
			</el-pagination>
		</div>
	</div>
</template>

<script>
	import * as echarts from "echarts";
	import {
		abortMediaScrapingJob,
		deleteMediaScrapingTask,
		getMediaScrapingJobCurrent,
		getMediaScrapingJobTasks,
		rerunMediaScrapingJob
	} from "@/api/mediaScraping";
	import filters from "@/utils/filters";

	export default {
		name: 'MediaScrapingTask',
		data() {
			return {
				taskData: {
					taskList: [],
					count: 0
				},
				params: {
					jobId: null,
					pageSize: 10,
					pageNum: 1
				},
				currentParams: {
					jobId: null,
					pageSize: 10,
					pageNum: 1,
					status: 1
				},
				current: null,
				currentHeight: 0,
				currentLoading: false,
				loading: false,
				btnLoading: false,
				timer: null,
				chart: null,
				currentStatus: 1,
				currentSpeed: 0,
				lastSnapshot: null,
				statusTabs: [{
					status: 0,
					label: '等待中',
					countKey: 'waitNum'
				}, {
					status: 1,
					label: '进行中',
					countKey: 'runningNum'
				}, {
					status: 2,
					label: '成功',
					countKey: 'successNum'
				}, {
					status: 7,
					label: '失败',
					countKey: 'failNum'
				}, {
					status: 3,
					label: '跳过',
					countKey: 'skipNum'
				}]
			};
		},
		computed: {
			avgSpeed() {
				if (!this.current || !Number(this.current.summary.elapsed || 0)) {
					return 0;
				}
				return Number(this.current.summary.finishedNum || 0) / Number(this.current.summary.elapsed || 1);
			},
			estimatedFinishText() {
				if (!this.current || !this.current.task.createTime ||
					this.current.summary.remaining === null || this.current.summary.remaining === undefined) {
					return '--';
				}
				return filters.timeStampFilter(Number(this.current.task.createTime) + Number(this.current.summary.elapsed || 0) +
					Number(this.current.summary.remaining || 0));
			}
		},
		created() {
			if (this.$route.query.hasOwnProperty('jobId')) {
				this.params.jobId = this.$route.query.jobId;
				this.currentParams.jobId = this.$route.query.jobId;
			}
			this.refreshAll();
		},
		mounted() {
			window.addEventListener('resize', this.resizeChart);
		},
		beforeDestroy() {
			this.stopPolling();
			window.removeEventListener('resize', this.resizeChart);
			if (this.chart) {
				this.chart.dispose();
				this.chart = null;
			}
		},
		methods: {
			rootRenameFromRequest(row) {
				let request = row && row.request;
				if (typeof request === 'string') {
					try {
						request = JSON.parse(request || '{}');
					} catch (e) {
						request = {};
					}
				}
				const plans = request && Array.isArray(request.plans) ? request.plans : [];
				for (const item of plans) {
					if (!item || !item.rootRenameFrom || !item.rootRenameTo || item.rootRenameFrom === item.rootRenameTo) {
						continue;
					}
					return {
						from: item.rootRenameFrom,
						to: item.rootRenameTo
					};
				}
				return null;
			},
			displayTaskPath(row) {
				if (row && row.displayPath && row.displayPath.includes('=>')) {
					return row.displayPath;
				}
				const rootRename = this.rootRenameFromRequest(row);
				if (rootRename) {
					return `${rootRename.from}=>${rootRename.to}`;
				}
				return (row && (row.displayPath || row.path)) || '-';
			},
			displayTaskName(row) {
				if (row && row.displayTaskName) {
					return row.displayTaskName;
				}
				const rootRename = this.rootRenameFromRequest(row);
				if (rootRename) {
					const parts = String(rootRename.to || '').split('/').filter(item => item);
					if (parts.length) {
						return parts[parts.length - 1];
					}
				}
				return (row && (row.taskName || row.path)) || '-';
			},
			refreshAll() {
				this.getCurrent(true);
				this.getTaskList();
			},
			getCurrent(showLoading = false) {
				if (!this.currentParams.jobId) {
					return;
				}
				this.currentLoading = showLoading;
				getMediaScrapingJobCurrent(this.currentParams).then(res => {
					this.currentLoading = false;
					if (!res.data) {
						this.current = null;
						this.currentHeight = 0;
						this.stopPolling();
						return;
					}
					this.updateSpeed(res.data.summary || {});
					this.current = {
						task: res.data.task || {},
						summary: res.data.summary || {},
						taskItemList: res.data.taskItemList || [],
						count: res.data.count || 0
					};
					this.currentHeight = 443;
					this.$nextTick(() => {
						this.initChart();
					});
					this.startPolling();
				}).catch(() => {
					this.currentLoading = false;
				})
			},
			getTaskList() {
				if (!this.params.jobId) {
					return;
				}
				this.loading = true;
				getMediaScrapingJobTasks(this.params).then(res => {
					this.loading = false;
					this.taskData = {
						taskList: res.data.taskList || [],
						count: res.data.count || 0
					};
				}).catch(() => {
					this.loading = false;
				})
			},
			updateSpeed(nextSummary) {
				const now = Date.now() / 1000;
				const finished = Number(nextSummary.finishedNum || 0);
				if (this.lastSnapshot) {
					const elapsed = now - this.lastSnapshot.time;
					const diff = finished - this.lastSnapshot.finished;
					if (elapsed > 0 && diff >= 0) {
						this.currentSpeed = diff / elapsed;
					}
				}
				this.lastSnapshot = {
					time: now,
					finished
				};
			},
			initChart() {
				if (!this.$refs.progressChart || !this.current) {
					return;
				}
				if (!this.chart) {
					this.chart = echarts.init(this.$refs.progressChart, 'dark');
				}
				const summary = this.current.summary || {};
				const data = [{
					name: '等待中',
					value: Number(summary.waitNum || 0)
				}, {
					name: '进行中',
					value: Number(summary.runningNum || 0)
				}, {
					name: '成功',
					value: Number(summary.successNum || 0)
				}, {
					name: '失败',
					value: Number(summary.failNum || 0)
				}, {
					name: '跳过',
					value: Number(summary.skipNum || 0)
				}];
				this.chart.setOption({
					color: ['rgb(79, 89, 104)', 'rgb(64, 158, 255)', 'rgb(103, 194, 58)', 'rgb(245, 108, 108)',
						'rgb(230, 162, 60)'
					],
					tooltip: {
						trigger: 'item'
					},
					legend: {
						top: '5%',
						left: 'center'
					},
					graphic: [{
						type: 'text',
						left: 'center',
						top: '58%',
						style: {
							text: `总数 ${Number(summary.allNum || 0)}\n完成 ${Number(summary.finishedNum || 0)}`,
							textAlign: 'center',
							fill: '#ffffff',
							fontSize: 15,
							lineHeight: 24,
							fontWeight: 600
						}
					}],
					series: [{
						name: '重命名数量',
						type: 'pie',
						radius: ['75%', '90%'],
						center: ['50%', '86%'],
						startAngle: 180,
						endAngle: 360,
						data
					}, {
						name: '重命名数量',
						type: 'pie',
						radius: [0, '65%'],
						center: ['50%', '86%'],
						startAngle: 180,
						endAngle: 360,
						label: {
							position: 'inside'
						},
						data
					}]
				});
			},
			resizeChart() {
				if (this.chart) {
					this.chart.resize();
				}
			},
			changeStatus(status) {
				if (this.currentStatus === status) {
					return;
				}
				this.currentStatus = status;
				this.currentParams.status = status;
				this.currentParams.pageNum = 1;
				this.getCurrent(true);
			},
			statusCount(item) {
				return Number((this.current && this.current.summary[item.countKey]) || 0);
			},
			startPolling() {
				if (this.timer) {
					return;
				}
				this.timer = setInterval(() => {
					this.getCurrent(false);
					this.getTaskList();
				}, 3000);
			},
			stopPolling() {
				if (!this.timer) {
					return;
				}
				clearInterval(this.timer);
				this.timer = null;
			},
			rerunJob() {
				if (!this.params.jobId) {
					return;
				}
				this.btnLoading = true;
				rerunMediaScrapingJob(this.params.jobId).then(() => {
					this.btnLoading = false;
					this.$message({
						message: '任务已重新进入后台执行',
						type: 'success'
					});
					this.refreshAll();
				}).catch(() => {
					this.btnLoading = false;
				})
			},
			abortJob() {
				if (!this.params.jobId) {
					return;
				}
				this.$confirm('中止任务不影响已完成的重命名项，未开始的重命名项将被取消，确定吗？', '提示', {
					confirmButtonText: '确定',
					cancelButtonText: '取消',
					type: 'warning'
				}).then(() => {
					this.btnLoading = true;
					abortMediaScrapingJob(this.params.jobId).then(() => {
						this.btnLoading = false;
						this.$message({
							message: '中止指令已发送，请等待中止完成',
							type: 'success'
						});
						this.refreshAll();
					}).catch(() => {
						this.btnLoading = false;
					})
				}).catch(() => {})
			},
			deleteTask(row) {
				this.$confirm('操作不可逆，将永久删除该执行日志，确定吗？', '提示', {
					confirmButtonText: '确定',
					cancelButtonText: '取消',
					type: 'warning'
				}).then(() => {
					this.btnLoading = true;
					deleteMediaScrapingTask(row.id).then(res => {
						this.btnLoading = false;
						this.$message({
							message: res.msg,
							type: 'success'
						});
						this.refreshAll();
					}).catch(() => {
						this.btnLoading = false;
					})
				}).catch(() => {})
			},
			detail(row) {
				this.$router.push({
					path: '/mediaScraping/task/item',
					query: {
						taskId: row.id,
						jobId: row.jobId || this.params.jobId
					}
				})
			},
			handleSizeChange(val) {
				this.params.pageSize = val;
				this.params.pageNum = 1;
				this.getTaskList();
			},
			handleCurrentChange(val) {
				this.params.pageNum = val;
				this.getTaskList();
			},
			handleCurrentSizeChange(val) {
				this.currentParams.pageSize = val;
				this.currentParams.pageNum = 1;
				this.getCurrent(true);
			},
			handleCurrentPageChange(val) {
				this.currentParams.pageNum = val;
				this.getCurrent(true);
			},
			goback() {
				this.$router.go(-1);
			},
			taskStatusText(status) {
				const map = {
					0: '等待',
					1: '运行中',
					2: '成功',
					3: '部分',
					4: '中止',
					6: '失败'
				};
				return map[Number(status)] || '未知';
			},
			taskStatusTag(status) {
				const map = {
					1: '',
					2: 'success',
					3: 'warning',
					4: 'info',
					6: 'danger'
				};
				return map[Number(status)] || 'info';
			},
			taskStatusBg(status) {
				const number = Number(status);
				return number < 6 ? number : 7;
			},
			taskItemStatusText(status) {
				const map = {
					0: '等待/未匹配',
					1: '进行中',
					2: '成功',
					3: '跳过',
					7: '失败'
				};
				return map[Number(status)] || '未知';
			},
			taskItemStatusTag(status) {
				const map = {
					2: 'success',
					3: 'info',
					7: 'danger'
				};
				return map[Number(status)] || 'warning';
			},
			itemStatusBg(status) {
				const number = Number(status);
				return number === 3 ? 3 : (number < 6 ? number : 7);
			},
			itemProgress(row) {
				if (row.progress !== undefined && row.progress !== null) {
					return Math.max(0, Math.min(100, Number(row.progress) || 0));
				}
				return Number(row.status) === 2 ? 100 : 0;
			},
			fileName(row) {
				const path = row.targetPath || row.srcPath || '';
				const parts = String(path).split('/').filter(item => item);
				return parts.length ? parts[parts.length - 1] : path;
			},
			sourceDir(row) {
				return this.parentPath(row.srcPath);
			},
			targetDir(row) {
				return this.parentPath(row.targetPath);
			},
			parentPath(path) {
				const parts = String(path || '').split('/').filter(item => item);
				parts.pop();
				return '/' + parts.join('/') + (parts.length ? '/' : '');
			},
			fileSize(row) {
				if (row.fileSize !== undefined && row.fileSize !== null) {
					return this.$options.filters.sizeFilter(row.fileSize);
				}
				return '--';
			},
			operationTypeText(row) {
				if (Number(row.status) === 3) {
					return '跳过';
				}
				return row.srcPath === row.targetPath ? '无变更' : '重命名';
			},
			operationTypeBg(row) {
				if (Number(row.status) === 3) {
					return 3;
				}
				return row.srcPath === row.targetPath ? 3 : 8;
			},
			reasonText(row) {
				if (row.errMsg === 'skip: target exists') {
					return '目标已存在，源文件保留未改名';
				}
				return row.errMsg || '';
			},
			formatDuration(value) {
				const total = Number(value || 0);
				const hours = Math.floor(total / 3600);
				const minutes = Math.floor((total % 3600) / 60);
				const seconds = Math.floor(total % 60);
				if (hours) {
					return `${hours}时${minutes}分${seconds}秒`;
				}
				if (minutes) {
					return `${minutes}分${seconds}秒`;
				}
				return `${seconds}秒`;
			},
			formatRemaining(value) {
				if (value === null || value === undefined) {
					return '计算中';
				}
				return this.formatDuration(value);
			},
			formatSpeed(value) {
				const number = Number(value || 0);
				if (number >= 10) {
					return number.toFixed(1);
				}
				return number.toFixed(2);
			},
			formatElapsed(value) {
				const num = Number(value || 0);
				return `${num.toFixed(2)}s`;
			}
		}
	}
</script>

<style lang="scss" scoped>
	.media-task {
		width: 100%;
		height: 100%;
		overflow-y: auto;
		padding: 16px;
		box-sizing: border-box;

		.top-box {
			display: flex;
			align-items: center;
			justify-content: space-between;
			margin-bottom: 16px;
		}

		.top-box-left {
			display: flex;
			align-items: center;
			gap: 12px;
		}

		.top-box-title {
			font-weight: bold;
		}

		.current-box {
			background-color: #100c2a;
			padding: 2px 10px;
			width: 100%;
			box-sizing: border-box;
			overflow-x: auto;
			transition: height 0.5s ease;
		}

		.current-box-top {
			min-width: 1100px;
			box-sizing: border-box;
			height: 56px;
			padding: 3px 0;
			border-bottom: 1px dotted #fff;
			display: flex;
			align-items: center;
			justify-content: space-between;
		}

		.current-box-top-left {
			flex: 1;
		}

		.current-box-top-right {
			width: 180px;
			display: flex;
			justify-content: center;
		}

		.top-line {
			display: flex;
			align-items: center;
			justify-content: center;
		}

		.top-line > div {
			width: 268px;
		}

		.top-field {
			display: flex;
			align-items: center;
		}

		.task-title-line {
			min-width: 1100px;
			height: 34px;
			display: flex;
			align-items: center;
			gap: 18px;
			color: #909bd4;
			border-bottom: 1px dotted rgba(255, 255, 255, .35);
		}

		.task-title-line span:first-child {
			color: #fff;
			font-weight: bold;
		}

		.current-box-bottom {
			min-width: 1100px;
			box-sizing: border-box;
			height: calc(100% - 90px);
			width: 100%;
			display: flex;
		}

		.current-echart-box {
			height: 100%;
			width: 40%;
			min-width: 390px;
			box-sizing: border-box;
			border-right: 1px dotted #fff;
		}

		.current-box-task {
			width: 60%;
			height: 100%;
			box-sizing: border-box;
			padding: 8px 0 8px 12px;
			display: flex;
		}

		.current-box-task-left {
			width: 72px;
			height: 100%;
		}

		.task-left-item {
			cursor: pointer;
			width: 72px;
			margin: 14px 0;
			padding: 3px 6px 3px 0;
			color: #4f5968;
			text-align: right;
			box-sizing: border-box;
			display: flex;
			align-items: center;
			justify-content: flex-end;
			gap: 4px;
		}

		.task-left-item b {
			min-width: 18px;
			font-size: 12px;
			font-weight: normal;
			color: inherit;
		}

		.task-left-item.is-current {
			color: #409eff;
			border-right: 3px solid #409eff;
			background-color: rgba(64, 158, 255, .4);
		}

		.current-box-task-right {
			margin-left: 8px;
			width: calc(100% - 80px);
			height: 100%;
		}

		.table-box {
			transition: height 0.5s ease;
		}

		.prgNum {
			font-size: 14px;
			padding: 1px 3px;
			text-align: center;
			font-weight: bold;
			margin: 1px 3px;
			min-width: 56px;
			border-radius: 3px;
		}

		.page {
			height: 63px;
			display: flex;
			align-items: center;
			justify-content: flex-end;
		}

		.page.compact {
			height: auto;
			margin-top: 8px;
		}

		.page-tip {
			flex: 1;
			display: flex;
			align-items: center;
		}

		.path-cell {
			word-break: break-all;
			line-height: 18px;
		}

		.path-cell.changed {
			color: #67c23a;
		}

		.stderr {
			color: #f56c6c;
		}

		.detail-expand {
			padding: 6px 20px;
		}

		.expand-row {
			display: flex;
			gap: 12px;
			line-height: 24px;
		}

		.expand-label {
			width: 70px;
			color: #909bd4;
			flex: none;
		}

		.expand-value {
			word-break: break-all;
		}
	}
</style>
