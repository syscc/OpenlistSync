<template>
	<div class="media-task" :style="`min-height: calc(320px + ${currentHeight}px)`">
		<div class="top-box">
			<div class="top-box-left">
					<el-button type="primary" size="small" @click="goback">{{ $t('common.back') }}</el-button>
					<el-button type="primary" size="small" @click="rerunJob"
					:loading="btnLoading">{{ $t('mediaScraping.manualRun') }}</el-button>
				</div>
			<div class="top-box-title">{{ $t('mediaScraping.jobDetail') }}</div>
					<el-button size="small" :loading="loading" @click="refreshAll">{{ $t('mediaScraping.refresh') }}</el-button>
		</div>

		<div class="current-box" v-if="current" :style="`height: ${currentHeight}px;`">
			<div class="current-box-top">
				<div class="current-box-top-left">
					<div class="top-line">
						<div class="top-field">
							{{ $t('mediaScraping.overallProgress') }}:
							<el-progress :stroke-width="20" :text-inside="true" style="width: 130px;"
								color="rgba(64, 158, 255, .8)" text-color="#fff"
								define-back-color="rgba(64, 158, 255, .3)"
								:percentage="Number(Number(current.summary.progress || 0).toFixed(4))"></el-progress>
						</div>
						<div>{{ $t('mediaScraping.currentStatus') }}: {{taskStatusText(current.task.status)}}</div>
						<div>{{ $t('mediaScraping.averageSpeed') }}: {{formatSpeed(avgSpeed)}} {{ $t('mediaScraping.itemsPerSecond') }}</div>
						<div>{{ $t('mediaScraping.instantSpeed') }}: {{formatSpeed(currentSpeed)}} {{ $t('mediaScraping.itemsPerSecond') }}</div>
					</div>
					<div class="top-line">
						<div>{{ $t('mediaScraping.duration') }}: {{formatDuration(current.summary.elapsed)}}</div>
						<div>{{ $t('mediaScraping.remaining') }}: {{formatRemaining(current.summary.remaining)}}</div>
							<div>{{ $t('mediaScraping.startedAt') }}: {{current.task.createTime ? timeStampFilter(current.task.createTime) : '--'}}</div>
						<div>{{ $t('mediaScraping.estimatedFinish') }}: {{estimatedFinishText}}</div>
					</div>
				</div>
				<div class="current-box-top-right">
					<el-button type="danger" @click="abortJob" :loading="btnLoading">{{ $t('mediaScraping.abortTask') }}</el-button>
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
							<span>{{ $t(item.labelKey) }}</span>
							<b>{{statusCount(item)}}</b>
						</div>
					</div>
					<div class="current-box-task-right">
						<el-table :data="current.taskItemList" height="calc(100% - 36px)" class="table-data"
							v-loading="currentLoading" :empty-text="$t('mediaScraping.noDetails')">
							<el-table-column type="expand">
									<template #default="props">
									<div class="detail-expand">
										<div class="expand-row">
											<span class="expand-label">{{ $t('mediaScraping.sourceDirectory') }}</span>
											<span class="expand-value">{{sourceDir(props.row)}}</span>
										</div>
										<div class="expand-row">
											<span class="expand-label">{{ $t('mediaScraping.targetDirectory') }}</span>
											<span class="expand-value">{{targetDir(props.row)}}</span>
										</div>
										<div class="expand-row">
											<span class="expand-label">{{ $t('common.createdAt') }}</span>
												<span class="expand-value">{{timeStampFilter(props.row.createTime)}}</span>
										</div>
										<div class="expand-row" v-if="props.row.errMsg">
											<span class="expand-label">{{ $t('common.reason') }}</span>
											<span class="expand-value stderr">{{reasonText(props.row)}}</span>
										</div>
									</div>
								</template>
							</el-table-column>
							<el-table-column :label="$t('mediaScraping.fileOrDirectory')" min-width="260">
									<template #default="scope">
									<div class="path-cell">{{fileName(scope.row)}}</div>
								</template>
							</el-table-column>
							<el-table-column :label="$t('mediaScraping.fileSize')" width="120">
									<template #default="scope">{{fileSize(scope.row)}}</template>
							</el-table-column>
							<el-table-column :label="$t('mediaScraping.operationType')" width="90">
									<template #default="scope">
									<div :class="`bg-status bg-${operationTypeBg(scope.row)}`" style="width: 58px;">
										{{operationTypeText(scope.row)}}
									</div>
								</template>
							</el-table-column>
							<el-table-column :label="$t('mediaScraping.status')" width="120">
									<template #default="scope">
									<el-progress :stroke-width="20" v-if="Number(scope.row.status) === 1" :text-inside="true"
										style="width: 90px;" color="rgba(64, 158, 255, .8)" text-color="#fff"
										define-back-color="rgba(64, 158, 255, .3)" :percentage="Number(itemProgress(scope.row).toFixed(3))"></el-progress>
									<div :class="`bg-status bg-${itemStatusBg(scope.row.status)}`" v-else>
										<span v-if="Number(scope.row.status) !== 7">{{taskItemStatusText(scope.row.status)}}</span>
										<el-popover v-else placement="top-end" :title="$t('mediaScraping.failedReason')" width="220" trigger="hover"
											:content="reasonText(scope.row)">
												<template #reference>
													<span>{{ $t('mediaScraping.failureWithReason') }}</span>
												</template>
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
			<el-table :data="taskData.taskList" height="100%" class="table-data" v-loading="loading" :empty-text="$t('mediaScraping.noExecutionLogs')">
				<el-table-column type="index" :label="$t('mediaScraping.serial')" align="center" width="60"></el-table-column>
				<el-table-column :label="$t('mediaScraping.status')" width="110">
						<template #default="scope">
						<div :class="`bg-status bg-${taskStatusBg(scope.row.status)}`">
							{{taskStatusText(scope.row.status)}}
						</div>
					</template>
				</el-table-column>
				<el-table-column :label="$t('mediaScraping.taskProgress')" min-width="280">
						<template #default="scope">
						<span v-if="scope.row.status == 1">{{ $t('mediaScraping.runningProgressAbove') }}</span>
						<div style="display: flex;align-items: center;flex-wrap: wrap;" v-else>
							<span class="prgNum bg-8">{{ $t('mediaScraping.totalShort') }} {{scope.row.total || 0}}</span>
							<span class="prgNum bg-2">{{ $t('mediaScraping.successShort') }} {{scope.row.successNum || 0}}</span>
							<span class="prgNum bg-7">{{ $t('mediaScraping.failedShort') }} {{scope.row.failNum || 0}}</span>
							<span class="prgNum bg-3">{{ $t('mediaScraping.skippedShort') }} {{scope.row.skipNum || 0}}</span>
						</div>
					</template>
				</el-table-column>
				<el-table-column :label="$t('mediaScraping.elapsed')" width="100">
						<template #default="scope">{{formatElapsed(scope.row.elapsed)}}</template>
				</el-table-column>
				<el-table-column :label="$t('common.createdAt')" width="160">
						<template #default="scope">{{timeStampFilter(scope.row.createTime)}}</template>
				</el-table-column>
				<el-table-column :label="$t('common.operate')" width="190">
						<template #default="scope">
							<el-button type="danger" @click="deleteTask(scope.row)"
							:loading="btnLoading" :disabled="scope.row.status == 1"
								size="small">{{scope.row.status == 1 ? $t('mediaScraping.deleteUnavailable') : $t('common.delete')}}</el-button>
							<el-button type="primary" @click="detail(scope.row)"
								:loading="btnLoading" size="small" v-if="scope.row.total != 0 && Number(scope.row.status) !== 1">{{ $t('mediaScraping.detail') }}</el-button>
					</template>
				</el-table-column>
			</el-table>
		</div>
		<div class="page">
			<div class="page-tip">
				<span style="margin-right: 12px;">{{ $t('mediaScraping.progressLegend') }}:</span>
				<span class="prgNum bg-8">{{ $t('mediaScraping.totalCount') }}</span>
				<span class="prgNum bg-2">{{ $t('mediaScraping.success') }}</span>
				<span class="prgNum bg-3">{{ $t('mediaScraping.skipped') }}</span>
				<span class="prgNum bg-7">{{ $t('mediaScraping.failed') }}</span>
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
				chartCompact: null,
				themeObserver: null,
				currentStatus: 1,
				currentSpeed: 0,
				lastSnapshot: null,
					statusTabs: [{
						status: 0,
						labelKey: 'mediaScraping.waiting',
						countKey: 'waitNum'
					}, {
						status: 1,
						labelKey: 'mediaScraping.running',
						countKey: 'runningNum'
					}, {
						status: 2,
						labelKey: 'mediaScraping.success',
						countKey: 'successNum'
					}, {
						status: 7,
						labelKey: 'mediaScraping.failed',
						countKey: 'failNum'
					}, {
						status: 3,
						labelKey: 'mediaScraping.skipped',
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
		watch: {
			'$i18n.locale'() {
				this.$nextTick(() => this.initChart());
			}
		},
		created() {
			if (Object.prototype.hasOwnProperty.call(this.$route.query, 'jobId')) {
				this.params.jobId = this.$route.query.jobId;
				this.currentParams.jobId = this.$route.query.jobId;
			}
			this.refreshAll();
		},
		mounted() {
			window.addEventListener('resize', this.resizeChart);
			this.themeObserver = new MutationObserver(() => {
				if (!this.chart) return;
				this.chart.dispose();
				this.chart = null;
				this.$nextTick(() => this.initChart());
			});
			this.themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
		},
		beforeUnmount() {
			this.stopPolling();
			window.removeEventListener('resize', this.resizeChart);
			if (this.themeObserver) {
				this.themeObserver.disconnect();
				this.themeObserver = null;
			}
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
					} catch {
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
				const compact = window.innerWidth <= 768;
				this.chartCompact = compact;
				if (!this.chart) {
					this.chart = echarts.init(this.$refs.progressChart);
				}
				const summary = this.current.summary || {};
				const data = [{
					name: this.$t('mediaScraping.waiting'),
					value: Number(summary.waitNum || 0)
				}, {
					name: this.$t('mediaScraping.running'),
					value: Number(summary.runningNum || 0)
				}, {
					name: this.$t('mediaScraping.success'),
					value: Number(summary.successNum || 0)
				}, {
					name: this.$t('mediaScraping.failed'),
					value: Number(summary.failNum || 0)
				}, {
					name: this.$t('mediaScraping.skipped'),
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
						left: 'center',
						textStyle: { color: this.cssColor('--text-secondary') }
					},
					graphic: [{
						type: 'text',
						zlevel: 10,
						left: 'center',
						top: '58%',
						style: {
							text: `${this.$t('mediaScraping.totalCount')} ${Number(summary.allNum || 0)}\n${this.$t('mediaScraping.completed')} ${Number(summary.finishedNum || 0)}`,
							textAlign: 'center',
							fill: this.cssColor('--text-primary'),
							fontSize: 15,
							lineHeight: 24,
							fontWeight: 600
						}
					}],
					series: [{
						name: this.$t('mediaScraping.renameCount'),
						type: 'pie',
						radius: ['75%', '90%'],
						center: ['50%', '86%'],
						startAngle: 180,
						endAngle: 360,
						label: {
							show: !compact
						},
						labelLine: {
							show: !compact
						},
						data
					}, {
						name: this.$t('mediaScraping.renameCount'),
						type: 'pie',
						radius: [0, '65%'],
						center: ['50%', '86%'],
						startAngle: 180,
						endAngle: 360,
						label: {
							show: !compact,
							position: 'inside'
						},
						data
					}]
				});
			},
			resizeChart() {
				if (this.chart) {
					if ((window.innerWidth <= 768) !== this.chartCompact) {
						this.initChart();
					}
					this.chart.resize();
				}
			},
			cssColor(name) {
				return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
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
						message: this.$t('mediaScraping.rerunQueued'),
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
				this.$confirm(this.$t('mediaScraping.abortConfirm'), this.$t('common.tips'), {
					confirmButtonText: this.$t('common.confirm'),
					cancelButtonText: this.$t('common.cancel'),
					type: 'warning'
				}).then(() => {
					this.btnLoading = true;
					abortMediaScrapingJob(this.params.jobId).then(() => {
						this.btnLoading = false;
						this.$message({
							message: this.$t('mediaScraping.abortQueued'),
							type: 'success'
						});
						this.refreshAll();
					}).catch(() => {
						this.btnLoading = false;
					})
				}).catch(() => {})
			},
			deleteTask(row) {
				this.$confirm(this.$t('mediaScraping.deleteTaskConfirm'), this.$t('common.tips'), {
					confirmButtonText: this.$t('common.confirm'),
					cancelButtonText: this.$t('common.cancel'),
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
					0: 'mediaScraping.statusWaiting',
					1: 'mediaScraping.statusRunning',
					2: 'mediaScraping.statusSuccess',
					3: 'mediaScraping.statusPartial',
					4: 'mediaScraping.statusAborted',
					6: 'mediaScraping.statusFailed'
				};
				return this.$t(map[Number(status)] || 'mediaScraping.statusUnknown');
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
					0: 'mediaScraping.waitingUnmatched',
					1: 'mediaScraping.running',
					2: 'mediaScraping.success',
					3: 'mediaScraping.skipped',
					7: 'mediaScraping.failed'
				};
				return this.$t(map[Number(status)] || 'mediaScraping.statusUnknown');
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
					return filters.sizeFilter(row.fileSize);
				}
				return '--';
			},
			operationTypeText(row) {
				if (Number(row.status) === 3) {
					return this.$t('mediaScraping.skip');
				}
				return this.$t(row.srcPath === row.targetPath ? 'mediaScraping.unchanged' : 'mediaScraping.rename');
			},
			operationTypeBg(row) {
				if (Number(row.status) === 3) {
					return 3;
				}
				return row.srcPath === row.targetPath ? 3 : 8;
			},
			reasonText(row) {
				if (row.errMsg === 'skip: target exists') {
					return this.$t('mediaScraping.targetExists');
				}
				return row.errMsg || '';
			},
			formatDuration(value) {
				const total = Number(value || 0);
				const hours = Math.floor(total / 3600);
				const minutes = Math.floor((total % 3600) / 60);
				const seconds = Math.floor(total % 60);
				if (hours) {
					return this.$t('mediaScraping.durationHours', { hours, minutes, seconds });
				}
				if (minutes) {
					return this.$t('mediaScraping.durationMinutes', { minutes, seconds });
				}
				return this.$t('mediaScraping.durationSeconds', { seconds });
			},
			formatRemaining(value) {
				if (value === null || value === undefined) {
					return this.$t('mediaScraping.calculating');
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
			background-color: var(--home-item-background-color);
			border: 1px solid var(--border-color);
			border-radius: 6px;
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
			border-bottom: 1px solid var(--border-color);
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
			color: var(--text-muted);
			border-bottom: 1px solid var(--border-color);
		}

		.task-title-line span:first-child {
			color: var(--text-primary);
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
			border-right: 1px solid var(--border-color);
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
			color: var(--text-muted);
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
			color: var(--text-muted);
			flex: none;
		}

		.expand-value {
			word-break: break-all;
		}
	}

	@media (max-width: 1000px) {
		.media-task {
			.current-box {
				height: auto !important;
				overflow: visible;
			}

			.current-box-top,
			.task-title-line,
			.current-box-bottom {
				min-width: 0;
			}

			.current-box-top {
				height: auto;
				min-height: 70px;
				gap: 12px;
			}

			.current-box-top-left {
				padding: 8px 0;
			}

			.top-line {
				display: grid;
				grid-template-columns: repeat(2, minmax(0, 1fr));
				gap: 8px 14px;
				justify-content: stretch;
			}

			.top-line + .top-line {
				margin-top: 8px;
			}

			.top-line > div {
				width: auto;
				min-width: 0;
			}

			.current-box-top-right {
				width: auto;
				padding-right: 4px;
			}

			.task-title-line {
				height: auto;
				min-height: 34px;
				padding: 6px 0;
				flex-wrap: wrap;
				word-break: break-all;
			}

			.current-box-bottom {
				height: auto;
				display: grid;
				grid-template-columns: minmax(0, 1fr);
			}

			.current-echart-box {
				width: 100%;
				height: 260px;
				min-width: 0;
				border-right: 0;
				border-bottom: 1px solid var(--border-color);
			}

			.current-box-task {
				width: 100%;
				height: 430px;
				padding: 8px 0;
				display: block;
			}

			.current-box-task-left {
				width: 100%;
				height: 42px;
				display: flex;
				overflow-x: auto;
			}

			.task-left-item {
				width: auto;
				min-width: 82px;
				height: 36px;
				margin: 0 4px 0 0;
				padding: 4px 8px;
				justify-content: center;
				text-align: center;
			}

			.task-left-item.is-current {
				border-right: 0;
				border-bottom: 3px solid var(--active-color);
			}

			.current-box-task-right {
				width: 100%;
				height: calc(100% - 42px);
				margin-left: 0;
			}

			.table-box {
				height: 420px !important;
				margin-top: 14px;
			}
		}
	}

	@media (max-width: 768px) {
		.media-task {
			height: auto;
			min-height: 100% !important;
			overflow: visible;
			padding: 12px 10px 20px;

			.top-box {
				align-items: center;
				flex-wrap: wrap;
				gap: 10px;
			}

			.top-box-title {
				order: -1;
				width: 100%;
			}

			.top-box-left {
				gap: 8px;
			}

			.current-box {
				padding: 6px 10px 10px;
			}

			.current-box-top {
				display: block;
			}

			.top-line {
				grid-template-columns: minmax(0, 1fr);
			}

			.current-box-top-right {
				justify-content: flex-start;
				padding: 0 0 10px;
			}

			.current-echart-box {
				height: 230px;
			}

			.current-box-task {
				height: 450px;
			}

			.page {
				height: auto;
				min-height: 63px;
				flex-wrap: wrap;
				gap: 10px;
				justify-content: center;
				overflow-x: auto;
			}

			.page-tip {
				width: 100%;
				flex: 1 0 100%;
				flex-wrap: wrap;
			}

			.detail-expand {
				padding: 6px 8px;
			}

			.expand-row {
				display: block;
				margin-bottom: 8px;
			}

			.expand-label {
				display: block;
				width: auto;
			}
		}
	}
</style>
