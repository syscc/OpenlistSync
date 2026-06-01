<template>
	<div class="task" :style="`min-height: calc(320px + ${currentHeight}px)`">
		<div class="top-box">
			<div class="top-box-left">
				<el-button type="primary" icon="el-icon-back" size="small" @click="goback">返回</el-button>
				<el-button type="primary" icon="el-icon-caret-right" size="small" @click="runJob"
					:loading="btnLoading">手动执行</el-button>
			</div>
			<div class="top-box-title">作业详情</div>
			<menuRefresh :loading="loading" :autoRefresh="false" :needShow="1" @getData="getTaskList"></menuRefresh>
		</div>
		<taskCurrent @currentChange="currentChange" class="task-current" :style="`height: ${currentHeight}px;`"
			:jobId="params.id"></taskCurrent>
		<div class="table-box" :style="`height: calc(100% - 117px - ${currentHeight}px);`">
			<el-table :data="taskData.taskList" height="100%" class="table-data" v-loading="loading" empty-text="暂无任务">
				<el-table-column type="index" label="序号" align="center" width="60"></el-table-column>
				<el-table-column prop="status" label="状态" width="110">
					<template slot-scope="scope">
						<div :class="`bg-status bg-${scope.row.status < 6 ? scope.row.status : 7}`">
							<template v-if="scope.row.status == 1 && scope.row.allNum == 0">
								扫描同步中
							</template>
							<template v-else-if="scope.row.status == 2 && scope.row.allNum == 0">
								无需同步
							</template>
							<template v-else>
								<span v-if="scope.row.status != 6">
									{{scope.row.status | taskStatusFilter}}
								</span>
								<el-popover v-else placement="top-end" title="错误原因" width="200" trigger="hover"
									:content="scope.row.errMsg">
									<span slot="reference">失败，<span style="color: #409eff;">原因</span></span>
								</el-popover>
							</template>
						</div>
					</template>
				</el-table-column>
				<el-table-column prop="successNum" label="任务进度（意义见页面底部图例，单位个）">
					<template slot-scope="scope">
						<span v-if="scope.row.status == 1">同步中的任务进度见👆</span>
						<div style="display: flex;align-items: center;flex-wrap: wrap;" v-else>
							<span class="prgNum bg-8">{{scope.row.allNum}}</span>
							<span class="prgNum bg-2">{{scope.row.successNum}}</span>
							<span class="prgNum bg-7">{{scope.row.failNum}}</span>
							<span class="prgNum bg-3">{{scope.row.otherNum}}</span>
						</div>
					</template>
				</el-table-column>
				<el-table-column prop="alarmTime" label="创建时间" width="160">
					<template slot-scope="scope">
						{{scope.row.createTime | timeStampFilter}}
					</template>
				</el-table-column>
				<el-table-column label="操作" width="180">
					<template slot-scope="scope">
						<el-button type="danger" icon="el-icon-delete" @click="delTask(scope.row.id)"
							:loading="btnLoading" :disabled="scope.row.status == 1"
							size="mini">{{scope.row.status == 1 ? '暂不能' : ''}}删除</el-button>
						<el-button type="primary" icon="el-icon-view" @click="detail(scope.row)"
							:loading="btnLoading" size="mini" v-if="scope.row.allNum != 0">详情</el-button>
					</template>
				</el-table-column>
			</el-table>
		</div>
		<div class="page">
			<div class="page-tip">
				<span style="margin-right: 12px;">进度图例：</span>
				<span class="prgNum bg-8">需同步文件和目录总数</span>
				<span class="prgNum bg-2">成功</span>
				<span class="prgNum bg-7">失败</span>
				<span class="prgNum bg-3">其他</span>
			</div>
			<el-pagination @size-change="handleSizeChange" @current-change="handleCurrentChange"
				:current-page="params.pageNum" :page-size="params.pageSize" :total="taskData.count"
				layout="total, sizes, prev, pager, next, jumper" :page-sizes="[10, 20, 50, 100]">
			</el-pagination>
		</div>
	</div>
</template>

<script>
	import {
		jobGetTask,
		jobDeleteTask,
		jobPut
	} from "@/api/job";
	import menuRefresh from './components/menuRefresh';
	import taskCurrent from './components/taskCurrent';
	export default {
		name: 'Task',
		components: {
			menuRefresh,
			taskCurrent
		},
		data() {
			return {
				taskData: {
					taskList: [],
					count: 0
				},
				params: {
					id: null,
					pageSize: 10,
					pageNum: 1
				},
				loading: false,
				btnLoading: false,
				currentHeight: 0
			};
		},
		created() {
			if (this.$route.query.hasOwnProperty('jobId')) {
				this.params.id = this.$route.query.jobId;
			}
		},
		beforeDestroy() {},
		methods: {
			getTaskList() {
				if (this.params.id != null) {
					this.loading = true;
					jobGetTask(this.params).then(res => {
						this.loading = false;
						this.taskData = {
							taskList: res.data.taskList,
							count: res.data.count
						};
					}).catch(err => {
						this.loading = false;
					})
				}
			},
			delTask(taskId) {
				this.$confirm("操作不可逆，将永久删除该记录，确定吗？", '提示', {
					confirmButtonText: '确定',
					cancelButtonText: '取消',
					type: 'warning'
				}).then(() => {
					this.btnLoading = true;
					jobDeleteTask(taskId).then(res => {
						this.btnLoading = false;
						this.$message({
							message: res.msg,
							type: 'success'
						});
						this.getTaskList();
					}).catch(err => {
						this.btnLoading = false;
					})
					});
				},
			runJob() {
				if (this.params.id == null) {
					this.$message.error("未找到所属作业，无法手动执行");
					return;
				}
				this.btnLoading = true;
				jobPut({
					id: this.params.id,
					pause: null
				}).then(res => {
					this.btnLoading = false;
					this.$message({
						message: res.msg,
						type: 'success'
					});
				}).catch(err => {
					this.btnLoading = false;
				})
			},
			detail(row) {
				this.$router.push({
					path: '/home/task/detail',
					query: {
						taskId: row.id,
						jobId: row.jobId || this.params.id
					}
				})
			},
			goback() {
				this.$router.go(-1);
			},
			handleSizeChange(val) {
				this.params.pageSize = val;
				this.getTaskList();
			},
			handleCurrentChange(val) {
				this.params.pageNum = val;
				this.getTaskList();
			},
			currentChange(val) {
				this.currentHeight = val;
				this.getTaskList();
			}
		}
	}
</script>

<style lang="scss" scoped>
	.task {
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

				.top-box-left {
					display: flex;
					align-items: center;
					gap: 12px;
				}

				.top-box-title {
				font-weight: bold;
			}
		}

		.task-current {
			transition: height 0.5s ease;
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

		.prgNum:last-child {
			margin-right: 0;
		}

		.page {
			margin-top: 24px;
			display: flex;
			align-items: center;
			justify-content: space-between;
		}
	}
</style>
