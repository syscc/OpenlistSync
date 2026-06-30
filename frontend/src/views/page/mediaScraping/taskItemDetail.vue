<template>
	<div class="media-task-detail">
		<div class="top-box">
			<div class="top-box-left">
				<el-button type="primary" icon="el-icon-caret-right" @click="rerunTask" size="small"
					:loading="btnLoading">手动执行</el-button>
				<el-button type="primary" icon="el-icon-back" @click="goback" size="small">返回</el-button>
				<el-select v-model="params.status" placeholder="筛选状态" @change="handleFilterChange" clearable
					size="small" class="filter-select">
					<el-option label="等待/未匹配" :value="0"></el-option>
					<el-option label="进行中" :value="1"></el-option>
					<el-option label="成功" :value="2"></el-option>
					<el-option label="跳过" :value="3"></el-option>
					<el-option label="失败" :value="7"></el-option>
				</el-select>
				<el-select v-model="params.type" placeholder="筛选操作类型" @change="handleFilterChange" clearable
					size="small" class="filter-select">
					<el-option label="重命名" :value="0"></el-option>
					<el-option label="跳过" :value="3"></el-option>
					<el-option label="失败" :value="7"></el-option>
				</el-select>
			</div>
			<div class="top-box-title">任务详情</div>
			<el-button size="small" icon="el-icon-refresh" :loading="loading" @click="getTaskItemList">刷新</el-button>
		</div>

		<div class="current-box" v-if="Number(task.status) === 1">
			<div class="current-box-top">
				<div class="current-box-top-left">
					<div class="top-line">
						<div class="top-field">
							整体进度：
							<el-progress :stroke-width="20" :text-inside="true" style="width: 130px;"
								color="rgba(64, 158, 255, .8)" text-color="#fff"
								define-back-color="rgba(64, 158, 255, .3)"
								:percentage="Number(Number(summary.progress || 0).toFixed(4))"></el-progress>
						</div>
						<div>当前状态：{{taskStatusText(task.status)}}</div>
						<div>平均速度：{{formatSpeed(avgSpeed)}} 个/s</div>
						<div>瞬时速度：{{formatSpeed(currentSpeed)}} 个/s</div>
					</div>
					<div class="top-line">
						<div>持续时间：{{formatDuration(summary.elapsed)}}</div>
						<div>预计还要：{{formatRemaining(summary.remaining)}}</div>
						<div>开始时间：{{task.createTime ? (task.createTime | timeStampFilter) : '--'}}</div>
						<div>预计完成：{{estimatedFinishText}}</div>
					</div>
				</div>
				<div class="current-box-top-right">
					<el-button type="danger" @click="abortTask" :loading="btnLoading">中止任务</el-button>
				</div>
			</div>
			<div class="task-title-line">
				<span>{{displayTaskName(task)}}</span>
				<span>{{displayTaskPath(task)}}</span>
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
						<el-table :data="taskItemData.taskItemList" height="calc(100% - 36px)" class="table-data"
							v-loading="loading" empty-text="暂无明细">
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
							<el-pagination small @size-change="handleSizeChange" @current-change="handleCurrentChange"
								:current-page="params.pageNum" :page-size="params.pageSize" :total="taskItemData.count"
								layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]">
							</el-pagination>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="table-box" v-else>
			<el-table :data="taskItemData.taskItemList" height="100%" class="table-data" v-loading="loading"
				empty-text="暂无明细">
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
				<el-table-column type="index" label="序号" align="center" width="60"></el-table-column>
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
						<div :class="`bg-status bg-${itemStatusBg(scope.row.status)}`" v-if="Number(scope.row.status) !== 1">
							<span v-if="Number(scope.row.status) !== 7">{{taskItemStatusText(scope.row.status)}}</span>
							<el-popover v-else placement="top-end" title="错误原因" width="220" trigger="hover"
								:content="reasonText(scope.row)">
								<span slot="reference">失败，<span style="color: #409eff;">原因</span></span>
							</el-popover>
						</div>
						<el-progress :stroke-width="20" v-else :text-inside="true" style="width: 90px;"
							color="rgba(64, 158, 255, .8)" text-color="#fff" define-back-color="rgba(64, 158, 255, .3)"
							:percentage="Number(itemProgress(scope.row).toFixed(3))"></el-progress>
					</template>
				</el-table-column>
			</el-table>
			<div class="page">
				<el-pagination @size-change="handleSizeChange" @current-change="handleCurrentChange"
					:current-page="params.pageNum" :page-size="params.pageSize" :total="taskItemData.count"
					layout="total, sizes, prev, pager, next, jumper" :page-sizes="[10, 20, 50, 100]">
				</el-pagination>
			</div>
		</div>
	</div>
</template>

<script>
	import * as echarts from "echarts";
	import {
		abortMediaScrapingTask,
		getMediaScrapingTaskItems,
		rerunMediaScrapingTask
	} from "@/api/mediaScraping";
	import filters from "@/utils/filters";

	export default {
		name: 'MediaScrapingTaskDetail',
		data() {
			return {
				task: {},
				summary: {},
				taskItemData: {
					taskItemList: [],
					count: 0
				},
				params: {
					taskId: null,
					pageSize: 10,
					pageNum: 1,
					status: null,
					type: null,
					all: true
				},
				loading: false,
				requesting: false,
				btnLoading: false,
				timer: null,
				chart: null,
				currentStatus: 1,
				statusInitialized: false,
				statusTouched: false,
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
				const elapsed = Number(this.summary.elapsed || 0);
				if (!elapsed) {
					return 0;
				}
				return Number(this.summary.finishedNum || 0) / elapsed;
			},
			estimatedFinishText() {
				if (!this.task.createTime || this.summary.remaining === null || this.summary.remaining === undefined) {
					return '--';
				}
				return filters.timeStampFilter(Number(this.task.createTime) + Number(this.summary.elapsed || 0) +
					Number(this.summary.remaining || 0));
			}
		},
		created() {
			if (this.$route.query.hasOwnProperty('taskId')) {
				this.params.taskId = this.$route.query.taskId;
			}
			this.getTaskItemList();
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
			getTaskItemList(showLoading = true) {
				if (!this.params.taskId || this.requesting) {
					return;
				}
				this.requesting = true;
				if (showLoading) {
					this.loading = true;
				}
				getMediaScrapingTaskItems(this.params).then(res => {
					this.requesting = false;
					if (showLoading) {
						this.loading = false;
					}
					const nextTask = res.data.task || {};
					const nextSummary = res.data.summary || {};
					if (Number(nextTask.status) === 1 && !this.statusTouched) {
						const defaultStatus = this.resolveDefaultStatus(nextTask, nextSummary);
						if (this.params.status === null || defaultStatus !== this.currentStatus &&
							(!this.statusInitialized || this.statusValueCount(nextSummary, this.currentStatus) === 0)) {
							this.statusInitialized = true;
							this.currentStatus = defaultStatus;
							this.params.status = defaultStatus;
							this.params.pageNum = 1;
							this.getTaskItemList(showLoading);
							return;
						}
					} else if (Number(nextTask.status) !== 1 && !this.statusTouched && this.params.status !== null) {
						this.params.status = null;
						this.params.pageNum = 1;
						this.getTaskItemList(showLoading);
						return;
					}
					this.statusInitialized = true;
					this.task = nextTask;
					this.updateSpeed(nextSummary);
					this.summary = nextSummary;
					this.taskItemData = {
						taskItemList: res.data.taskItemList || [],
						count: res.data.count || 0
					};
					this.$nextTick(() => {
						this.initChart();
					});
					if (Number(this.task.status) === 1) {
						this.startPolling();
					} else {
						this.stopPolling();
					}
				}).catch(() => {
					this.requesting = false;
					if (showLoading) {
						this.loading = false;
					}
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
			resolveDefaultStatus(task, summary) {
				const running = Number(summary.runningNum || 0);
				const wait = Number(summary.waitNum || 0);
				const success = Number(summary.successNum || 0);
				const fail = Number(summary.failNum || 0);
				const skip = Number(summary.skipNum || 0);
				if (Number(task.status) === 1) {
					if (running > 0) return 1;
					if (wait > 0) return 0;
				}
				if (success > 0) return 2;
				if (fail > 0) return 7;
				if (skip > 0) return 3;
				if (running > 0) return 1;
				if (wait > 0) return 0;
				return 1;
			},
			statusValueCount(summary, status) {
				const map = {
					0: 'waitNum',
					1: 'runningNum',
					2: 'successNum',
					3: 'skipNum',
					7: 'failNum'
				};
				return Number(summary[map[status]] || 0);
			},
			statusCount(item) {
				return Number(this.summary[item.countKey] || 0);
			},
			initChart() {
				if (!this.$refs.progressChart) {
					return;
				}
				if (!this.chart) {
					this.chart = echarts.init(this.$refs.progressChart, 'dark');
				}
				const data = [{
					name: '等待中',
					value: Number(this.summary.waitNum || 0)
				}, {
					name: '进行中',
					value: Number(this.summary.runningNum || 0)
				}, {
					name: '成功',
					value: Number(this.summary.successNum || 0)
				}, {
					name: '失败',
					value: Number(this.summary.failNum || 0)
				}, {
					name: '跳过',
					value: Number(this.summary.skipNum || 0)
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
							text: `总数 ${Number(this.summary.allNum || 0)}\n完成 ${Number(this.summary.finishedNum || 0)}`,
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
				this.statusTouched = true;
				this.currentStatus = status;
				this.params.status = status;
				this.params.pageNum = 1;
				this.getTaskItemList();
			},
			handleFilterChange() {
				this.statusTouched = this.params.status !== null && this.params.status !== undefined && this.params.status !== '';
				if (this.params.status !== null && this.params.status !== undefined && this.params.status !== '') {
					this.currentStatus = this.params.status;
				}
				this.params.pageNum = 1;
				this.getTaskItemList();
			},
			startPolling() {
				if (this.timer) {
					return;
				}
				this.timer = setInterval(() => {
					this.getTaskItemList(false);
				}, 3000);
			},
			stopPolling() {
				if (!this.timer) {
					return;
				}
				clearInterval(this.timer);
				this.timer = null;
			},
			rerunTask() {
				if (!this.params.taskId) {
					return;
				}
				this.$confirm('将按该日志保存的参数重新执行重命名，是否继续？', '再次执行', {
					confirmButtonText: '执行',
					cancelButtonText: '取消',
					type: 'warning'
				}).then(() => {
					this.btnLoading = true;
					rerunMediaScrapingTask(this.params.taskId).then(res => {
						this.btnLoading = false;
						this.$message({
							message: '任务已重新进入后台执行',
							type: 'success'
						});
						this.params.taskId = res.data.taskId;
						this.params.pageNum = 1;
						this.currentStatus = 1;
						this.params.status = 1;
						this.statusInitialized = false;
						this.statusTouched = false;
						this.$router.replace({
							path: '/mediaScraping/task/item',
							query: {
								taskId: this.params.taskId,
								jobId: res.data.jobId || this.$route.query.jobId
							}
						});
						this.getTaskItemList();
					}).catch(() => {
						this.btnLoading = false;
					})
				}).catch(() => {})
			},
			abortTask() {
				if (!this.params.taskId) {
					return;
				}
				this.$confirm('中止任务不影响已完成的重命名项，未开始的重命名项将被取消，确定吗？', '提示', {
					confirmButtonText: '确定',
					cancelButtonText: '取消',
					type: 'warning'
				}).then(() => {
					this.btnLoading = true;
					abortMediaScrapingTask(this.params.taskId).then(() => {
						this.btnLoading = false;
						this.$message({
							message: '中止指令已发送，请等待中止完成',
							type: 'success'
						});
						this.getTaskItemList();
					}).catch(() => {
						this.btnLoading = false;
					})
				}).catch(() => {})
			},
			handleSizeChange(val) {
				this.params.pageSize = val;
				this.params.pageNum = 1;
				this.getTaskItemList();
			},
			handleCurrentChange(val) {
				this.params.pageNum = val;
				this.getTaskItemList();
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
					2: 'success',
					3: 'warning',
					4: 'info',
					6: 'danger'
				};
				return map[Number(status)] || 'info';
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
				if (Number(row.status) === 7) {
					return '重命名';
				}
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
			}
		}
	}
</script>

<style lang="scss" scoped>
	.media-task-detail {
		width: 100%;
		height: 100%;
		padding: 16px;
		box-sizing: border-box;
		overflow: auto;

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

		.filter-select {
			width: 150px;
		}

		.top-box-title {
			font-weight: bold;
			display: flex;
			align-items: center;
			gap: 8px;
		}

		.current-box {
			background-color: #100c2a;
			height: calc(100% - 48px);
			min-height: 520px;
			padding: 2px 10px;
			width: 100%;
			box-sizing: border-box;
			overflow-x: auto;
		}

		.table-box {
			height: calc(100% - 54px);
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

		.page {
			margin-top: 8px;
			display: flex;
			justify-content: flex-end;
		}

		.page.compact {
			justify-content: flex-end;
		}
	}
</style>
