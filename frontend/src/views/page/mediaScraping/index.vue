<template>
	<div class="media-scraping-page">
		<div class="page-title">媒体名字刮削</div>
		<div class="workbench">
			<div class="panel browser-panel">
				<div class="panel-title">媒体路径</div>
				<div class="default-engine">
					<div>
						<div class="engine-label">默认引擎</div>
						<div class="engine-name">{{selectedEngineName}}</div>
					</div>
					<el-button size="small" @click="toScrapingConfig">刮削配置</el-button>
				</div>
				<div class="path-bar">
					<el-input v-model="currentPath" size="small" placeholder="粘贴路径后回车跳转" @keyup.enter.native="browsePath(currentPath)">
						<el-button slot="append" @click="browsePath(currentPath)">跳转</el-button>
					</el-input>
				</div>
				<div class="browser-actions">
					<el-button size="mini" icon="el-icon-back" @click="goParent">上级</el-button>
					<el-button size="mini" icon="el-icon-refresh" :loading="browseLoading" title="强制刷新目录"
						@click="browsePath(currentPath, true)">刷新</el-button>
				</div>
				<div class="file-list" v-loading="browseLoading">
					<div class="file-row" v-for="item in browserItems" :key="item.path" :class="{disabled: !item.isDir}"
						@click="item.isDir && browsePath(item.path)">
						<i :class="item.isDir ? 'el-icon-folder' : 'el-icon-document'"></i>
						<span>{{item.name}}</span>
					</div>
					<div v-if="browserItems.length === 0 && !browseLoading" class="empty">暂无内容</div>
				</div>
			</div>

			<div class="panel preview-panel">
				<div class="preview-top">
					<div>
						<div class="panel-title">命名预览</div>
						<div class="current-path">{{currentPath}}</div>
					</div>
				</div>
				<div class="preview-tools">
					<el-select v-model="mediaType" size="small" class="type-select" @change="clearPreview">
						<el-option label="自动识别" value="auto"></el-option>
						<el-option label="电影" value="movie"></el-option>
						<el-option label="电视剧" value="tv"></el-option>
					</el-select>
					<el-checkbox v-model="recursive" @change="clearPreview">递归</el-checkbox>
					<el-input-number v-model="config.limit" size="small" :min="0" controls-position="right" class="limit-input"
						@change="clearPreview"></el-input-number>
					<span class="tip-text">处理数量</span>
					<el-input v-model="tmdbId" size="small" class="tmdb-id-input" placeholder="TMDb ID" clearable
						@input="clearPreview">
						<el-button slot="append" icon="el-icon-search" title="搜索 TMDb" @click="openTmdbSearch"></el-button>
					</el-input>
					<el-input v-model="seasonNumber" size="small" class="season-input" placeholder="季数" clearable
						:disabled="mediaType === 'movie'" @input="clearPreview"></el-input>
					<span class="tip-text">季数</span>
					<el-button type="primary" size="small" :loading="previewLoading"
						:disabled="normalizePath(currentPath) === '/'"
						@click="previewNaming">
						预览命名
					</el-button>
					<el-button type="danger" size="small" :loading="runLoading" :disabled="previewLoading || previewItems.length === 0"
						@click="applyNaming">
						应用命名
					</el-button>
				</div>

				<div v-if="previewResult" class="preview-summary">
					<span>文件 {{previewResult.total}}</span>
					<span>变更 {{previewResult.changed}}</span>
					<span v-if="previewResult.duplicateTargets" class="conflict-text">目标冲突 {{previewResult.duplicateTargets}}</span>
					<span v-if="previewResult.limited">预览前 {{previewResult.previewLimit}} 项</span>
					<span v-if="previewResult.rootRenames && previewResult.rootRenames.length">目录重命名 {{previewResult.rootRenames.length}}</span>
				</div>
				<div v-if="previewResult && previewResult.rootRenames && previewResult.rootRenames.length" class="root-renames">
					<div v-for="item in previewResult.rootRenames" :key="item.from + item.to" class="root-rename-item">
						<div>{{item.from}}</div>
						<div>{{item.to}}</div>
					</div>
				</div>
				<el-table :data="previewItems" size="mini" class="preview-table" height="430" empty-text="选择路径后点击预览命名">
					<el-table-column label="原路径" min-width="280">
						<template slot-scope="scope">
							<div class="path-cell">{{scope.row.srcPath}}</div>
						</template>
					</el-table-column>
					<el-table-column label="命名后" min-width="280">
						<template slot-scope="scope">
							<div class="path-cell" :class="{changed: scope.row.changed, conflict: scope.row.duplicateTarget}">
								{{scope.row.targetPath}}
								<el-tag v-if="scope.row.duplicateTarget" size="mini" type="danger">目标冲突 {{scope.row.targetConflictCount}}</el-tag>
							</div>
						</template>
					</el-table-column>
				</el-table>

			</div>

		</div>
		<div class="panel task-log-panel">
			<div class="log-top">
				<div>
					<div class="panel-title">重命名任务</div>
					<div class="current-path">同一媒体目录的多次执行会归到同一个任务里</div>
				</div>
				<el-button size="small" icon="el-icon-refresh" :loading="taskLoading" @click="getTaskList">刷新</el-button>
			</div>
			<el-table :data="taskData.taskList" size="mini" class="task-table" height="260" empty-text="暂无重命名任务"
				v-loading="taskLoading">
				<el-table-column label="状态" width="90">
					<template slot-scope="scope">
						<el-tag size="mini" :type="taskStatusTag(scope.row.status)">{{taskStatusText(scope.row.status)}}</el-tag>
					</template>
				</el-table-column>
				<el-table-column label="任务" min-width="180">
					<template slot-scope="scope">
						<div class="path-cell">{{displayTaskName(scope.row)}}</div>
					</template>
				</el-table-column>
				<el-table-column label="路径" min-width="260">
					<template slot-scope="scope">
						<div class="path-cell">{{displayTaskPath(scope.row)}}</div>
					</template>
				</el-table-column>
				<el-table-column label="耗时" width="90">
					<template slot-scope="scope">{{formatElapsed(scope.row.elapsed)}}</template>
				</el-table-column>
				<el-table-column label="统计" width="190">
					<template slot-scope="scope">
						<span class="log-count">总 {{scope.row.total || 0}}</span>
						<span class="log-count ok">成 {{scope.row.successNum || 0}}</span>
						<span class="log-count skip">跳 {{scope.row.skipNum || 0}}</span>
						<span class="log-count fail">败 {{scope.row.failNum || 0}}</span>
					</template>
				</el-table-column>
				<el-table-column label="时间" width="150">
					<template slot-scope="scope">{{(scope.row.updateTime || scope.row.createTime) | timeStampFilter}}</template>
				</el-table-column>
				<el-table-column label="操作" width="250">
					<template slot-scope="scope">
						<el-button size="mini" type="primary" icon="el-icon-caret-right" @click="manualRunTask(scope.row)"
							:loading="taskActionLoading">手动执行</el-button>
						<el-button size="mini" type="primary" @click="detailTask(scope.row)">详情</el-button>
						<el-button size="mini" type="danger" @click="deleteTask(scope.row)">删除</el-button>
					</template>
				</el-table-column>
			</el-table>
			<div class="page-line">
				<el-pagination small @size-change="handleTaskSizeChange" @current-change="handleTaskCurrentChange"
					:current-page="taskParams.pageNum" :page-size="taskParams.pageSize" :total="taskData.count"
					layout="total, sizes, prev, pager, next" :page-sizes="[10, 20, 50, 100]">
				</el-pagination>
			</div>
		</div>
		<div v-if="tmdbSearchVisible" class="tmdb-search-mask" @click.self="closeTmdbSearch">
			<div class="tmdb-search-panel" @click.stop>
				<div class="tmdb-search-bar">
					<button class="tmdb-search-submit" type="button" title="搜索" @click="searchTmdb">
						<i class="el-icon-search"></i>
					</button>
					<input ref="tmdbSearchInput" v-model="tmdbSearchKeyword" class="tmdb-search-input" type="text"
						placeholder="电影或电视剧名称" @keydown.enter.prevent="searchTmdb">
					<button class="tmdb-search-close" type="button" title="关闭" @click="closeTmdbSearch">
						<i class="el-icon-close"></i>
					</button>
				</div>
				<div class="tmdb-result-list" v-loading="tmdbSearchLoading">
					<div v-for="item in tmdbSearchResults" :key="item.type + '-' + item.id" class="tmdb-result-item"
						@click="selectTmdbResult(item)">
						<div class="tmdb-poster">
							<img v-if="item.posterUrl" :src="item.posterUrl" :alt="item.title">
							<i v-else class="el-icon-picture-outline"></i>
						</div>
						<div class="tmdb-info">
							<div class="tmdb-title">
								<span>{{item.title}}</span>
								<span v-if="item.year">（{{item.year}}）</span>
								<el-tag size="mini" effect="dark" class="tmdb-type">{{item.typeText}}</el-tag>
								<span class="tmdb-id">ID {{item.id}}</span>
							</div>
							<div v-if="item.originalTitle && item.originalTitle !== item.title" class="tmdb-original">{{item.originalTitle}}</div>
							<div class="tmdb-overview">{{item.overview || '暂无简介'}}</div>
						</div>
					</div>
					<div v-if="tmdbSearchResults.length === 0 && tmdbSearched && !tmdbSearchLoading" class="empty">暂无结果</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
	import {
		openlistGet
	} from "@/api/job";
	import {
		browseMediaScraping,
		deleteMediaScrapingJob,
		getMediaScrapingConfig,
		getMediaScrapingTasks,
		previewMediaScraping,
		rerunMediaScrapingJob,
		runMediaScraping,
		searchMediaTmdb
	} from "@/api/mediaScraping";

	export default {
		name: 'MediaScraping',
		data() {
			return {
				openlistList: [],
				config: this.defaultConfig(),
				extensionsText: '',
				currentPath: '/',
				mediaType: 'auto',
				recursive: true,
				tmdbId: '',
				seasonNumber: '',
				browserItems: [],
				previewResult: null,
				browseLoading: false,
				previewLoading: false,
				runLoading: false,
				previewSeq: 0,
				taskLoading: false,
				taskActionLoading: false,
				taskData: {
					taskList: [],
					count: 0
				},
				taskParams: {
					pageSize: 10,
					pageNum: 1
				},
				tmdbSearchVisible: false,
				tmdbSearchKeyword: '',
				tmdbSearchResults: [],
				tmdbSearchLoading: false,
				tmdbSearched: false
			};
		},
		computed: {
			previewItems() {
				return this.previewResult && this.previewResult.items ? this.previewResult.items : [];
			},
			selectedEngineName() {
				const engine = this.openlistList.find(item => item.id === this.config.defaultOpenlistId);
				if (!engine) {
					return '未配置';
				}
				return engine.remark || engine.url;
			}
		},
		created() {
			this.getOpenlistList();
			this.getConfig();
		},
		beforeDestroy() {},
		methods: {
			defaultConfig() {
				return {
					defaultOpenlistId: null,
					openlistIds: [],
					tmdbApiKey: '',
					tmdbBearerToken: '',
					tmdbLanguage: 'zh-CN',
					tmdbIncludeAdult: false,
					tmdbRequired: true,
					tmdbTimeout: 30,
					openlistTimeout: 30,
					dryRun: true,
					overwrite: false,
					refresh: false,
					limit: 0,
					renameThreads: 2,
					renameLogLimit: 10,
					movieTemplate: '',
					tvTemplate: '',
					mediaExtensions: [],
					customWords: '',
					customReleaseGroups: '',
					customization: '',
					rules: []
				};
			},
			getOpenlistList() {
				openlistGet().then(res => {
					this.openlistList = res.data || [];
					this.ensureDefaultEngine();
				})
			},
			getConfig() {
				getMediaScrapingConfig().then(res => {
					this.config = Object.assign(this.defaultConfig(), res.data || {});
					this.extensionsText = (this.config.mediaExtensions || []).join(',');
					this.ensureDefaultEngine();
					this.getTaskList();
				})
			},
			ensureDefaultEngine() {
				if (!this.config.defaultOpenlistId && this.config.openlistIds && this.config.openlistIds.length) {
					this.config.defaultOpenlistId = this.config.openlistIds[0];
				}
				if (!this.config.defaultOpenlistId && this.openlistList.length) {
					this.config.defaultOpenlistId = this.openlistList[0].id;
				}
				if (this.config.defaultOpenlistId && this.browserItems.length === 0) {
					this.browsePath(this.currentPath);
				}
			},
			buildConfig() {
				const defaultOpenlistId = this.config.defaultOpenlistId || null;
				return {
					...this.config,
					defaultOpenlistId,
					openlistIds: defaultOpenlistId ? [defaultOpenlistId] : [],
					mediaExtensions: (this.extensionsText || '').split(',').map(item => item.trim()).filter(item => item)
				};
			},
			requireEngine() {
				if (!this.config.defaultOpenlistId) {
					this.$message.error('请先选择默认OpenList引擎');
					return false;
				}
				return true;
			},
			normalizePath(path) {
				let value = (path || '/').trim();
				if (!value.startsWith('/')) {
					value = '/' + value;
				}
				return value.replace(/\/+/g, '/');
			},
			browsePath(path, refresh = false) {
				if (!this.requireEngine()) {
					return;
				}
				this.currentPath = this.normalizePath(path);
				this.clearPreview();
				if (refresh) {
					this.browserItems = [];
				}
				this.browseLoading = true;
				browseMediaScraping({
					openlistId: this.config.defaultOpenlistId,
					path: this.currentPath,
					refresh,
					config: this.buildConfig()
				}).then(res => {
					this.browserItems = res.data.items || [];
					this.currentPath = res.data.path || this.currentPath;
					this.browseLoading = false;
				}).catch(() => {
					this.browseLoading = false;
				})
			},
			goParent() {
				const parts = this.normalizePath(this.currentPath).split('/').filter(item => item);
				parts.pop();
				this.browsePath('/' + parts.join('/'));
			},
			clearPreview() {
				this.previewSeq += 1;
				this.previewLoading = false;
				this.previewResult = null;
			},
			defaultSearchKeyword() {
				const parts = this.normalizePath(this.currentPath).split('/').filter(item => item);
				const name = parts.length ? parts[parts.length - 1] : '';
				return name
					.replace(/\{tmdb-\d+\}/ig, '')
					.replace(/\[[^\]]+\]/g, ' ')
					.replace(/\([12]\d{3}\)/g, ' ')
					.replace(/[._-]+/g, ' ')
					.replace(/\s+/g, ' ')
					.trim();
			},
			openTmdbSearch() {
				this.tmdbSearchVisible = true;
				this.tmdbSearchResults = [];
				this.tmdbSearched = false;
				if (!this.tmdbSearchKeyword) {
					this.tmdbSearchKeyword = this.defaultSearchKeyword();
				}
				this.$nextTick(() => {
					if (this.$refs.tmdbSearchInput) {
						this.$refs.tmdbSearchInput.focus();
						this.$refs.tmdbSearchInput.select();
					}
				});
			},
			closeTmdbSearch() {
				this.tmdbSearchVisible = false;
			},
			searchTmdb() {
				const keyword = (this.tmdbSearchKeyword || '').trim();
				if (!keyword) {
					this.$message.error('请输入电影或电视剧名称');
					return;
				}
				this.tmdbSearchLoading = true;
				this.tmdbSearched = true;
				searchMediaTmdb({
					query: keyword,
					type: this.mediaType,
					config: this.buildConfig()
				}).then(res => {
					this.tmdbSearchResults = res.data.items || [];
					this.tmdbSearchLoading = false;
				}).catch(() => {
					this.tmdbSearchLoading = false;
				})
			},
			selectTmdbResult(item) {
				this.tmdbId = String(item.id || '');
				if (item.type === 'movie' || item.type === 'tv') {
					this.mediaType = item.type;
				}
				this.tmdbSearchVisible = false;
				this.clearPreview();
			},
			previewNaming(silent = false) {
				if (!this.requireEngine()) {
					return;
				}
				if (this.normalizePath(this.currentPath) === '/') {
					this.previewResult = null;
					return;
				}
				const requestSeq = ++this.previewSeq;
				this.previewLoading = true;
				previewMediaScraping({
					openlistId: this.config.defaultOpenlistId,
					path: this.currentPath,
					type: this.mediaType,
					recursive: this.recursive,
					limit: this.config.limit,
					previewLimit: this.config.limit,
					tmdbId: this.tmdbId,
					seasonNumber: this.seasonNumber,
					config: this.buildConfig()
				}).then(res => {
					if (requestSeq !== this.previewSeq) {
						return;
					}
					this.previewResult = res.data;
					this.previewLoading = false;
				}).catch(() => {
					if (requestSeq !== this.previewSeq) {
						return;
					}
					if (silent) {
						this.previewResult = null;
					}
					this.previewLoading = false;
				})
			},
			applyNaming() {
				if (!this.requireEngine()) {
					return;
				}
				this.$confirm('将直接调用 OpenList 重命名、移动文件或创建目录，是否继续？', '确认应用命名', {
					confirmButtonText: '应用',
					cancelButtonText: '取消',
					type: 'warning'
					}).then(() => {
						this.runLoading = true;
						const config = this.buildConfig();
					config.rules = [{
						path: this.currentPath,
						type: this.mediaType,
						recursive: this.recursive,
						tmdbId: this.tmdbId,
						seasonNumber: this.seasonNumber
					}];
					runMediaScraping({
						apply: true,
						path: this.currentPath,
						type: this.mediaType,
						recursive: this.recursive,
						limit: this.config.limit,
						tmdbId: this.tmdbId,
						seasonNumber: this.seasonNumber,
						plans: this.previewItems,
						config
						}).then(() => {
							this.$message({
								message: '任务已在后台执行，可在重命名任务中查看进度',
								type: 'success'
							});
							this.runLoading = false;
							this.getTaskList();
						}).catch(() => {
							this.runLoading = false;
						})
				}).catch(() => {})
			},
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
			getTaskList() {
				this.taskLoading = true;
				getMediaScrapingTasks(this.taskParams).then(res => {
					this.taskData = {
						taskList: res.data.taskList || [],
						count: res.data.count || 0
					};
					this.taskLoading = false;
				}).catch(() => {
					this.taskLoading = false;
				})
			},
			deleteTask(row) {
				this.$confirm('操作不可逆，将永久删除该重命名任务及其全部执行日志，确定吗？', '提示', {
					confirmButtonText: '确定',
					cancelButtonText: '取消',
					type: 'warning'
				}).then(() => {
					deleteMediaScrapingJob(row.id).then(res => {
						this.$message({
							message: res.msg,
							type: 'success'
						});
						this.getTaskList();
					})
				}).catch(() => {})
			},
			manualRunTask(row) {
				this.taskActionLoading = true;
				rerunMediaScrapingJob(row.id).then(() => {
					this.$message({
						message: '任务已重新进入后台执行',
						type: 'success'
					});
					this.taskActionLoading = false;
					this.getTaskList();
				}).catch(() => {
					this.taskActionLoading = false;
				})
			},
			handleTaskSizeChange(val) {
				this.taskParams.pageSize = val;
				this.taskParams.pageNum = 1;
				this.getTaskList();
			},
			handleTaskCurrentChange(val) {
				this.taskParams.pageNum = val;
				this.getTaskList();
			},
			detailTask(row) {
				this.$router.push({
					path: '/mediaScraping/task/detail',
					query: {
						jobId: row.id
					}
				});
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
			formatElapsed(value) {
				const num = Number(value || 0);
				return `${num.toFixed(2)}s`;
			},
			toScrapingConfig() {
				this.$router.push({
					path: '/engine',
					query: {
						type: 'mediaScraping'
					}
				});
			}
		}
	}
</script>

<style lang="scss" scoped>
	.media-scraping-page {
		padding: 24px;
		width: 100%;
		box-sizing: border-box;

		.page-title {
			font-size: 20px;
			font-weight: bold;
			margin-bottom: 16px;
		}

		.workbench {
			display: grid;
			grid-template-columns: 320px minmax(520px, 1fr);
			gap: 14px;
			align-items: stretch;
			height: 572px;
		}

		.panel {
			background-color: #292b3c;
			border-radius: 3px;
			padding: 16px;
			box-sizing: border-box;
			min-height: 160px;
		}

		.panel-title {
			font-size: 16px;
			font-weight: bold;
			margin-bottom: 12px;
		}

		.task-log-panel {
			margin-top: 12px;
		}

		.log-top {
			display: flex;
			align-items: flex-start;
			justify-content: space-between;
			gap: 14px;
			margin-bottom: 12px;
		}

		.page-line {
			display: flex;
			justify-content: flex-end;
			margin-top: 10px;
		}

		.log-count {
			margin-right: 8px;
			color: #909bd4;
		}

		.log-count.ok {
			color: #67c23a;
		}

		.log-count.skip {
			color: #909399;
		}

		.log-count.fail {
			color: #f56c6c;
		}

		.default-engine {
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: 10px;
			padding: 10px;
			background-color: rgba(255, 255, 255, .04);
			border-radius: 3px;
		}

		.engine-label {
			color: #909bd4;
			font-size: 12px;
			margin-bottom: 4px;
		}

		.engine-name {
			max-width: 190px;
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
		}

		.path-bar {
			margin-top: 12px;
		}

		.browser-panel,
		.preview-panel {
			height: 100%;
			display: flex;
			flex-direction: column;
			overflow: hidden;
		}

		.browser-actions {
			margin: 10px 0;
			display: flex;
			gap: 8px;
		}

		.file-list {
			flex: 1;
			min-height: 0;
			overflow: auto;
			border-top: 1px solid rgba(255, 255, 255, .08);
		}

		.file-row {
			height: 34px;
			display: flex;
			align-items: center;
			gap: 8px;
			padding: 0 4px;
			cursor: pointer;
			border-bottom: 1px solid rgba(255, 255, 255, .04);
		}

		.file-row:hover {
			background-color: rgba(64, 158, 255, .12);
		}

		.file-row.disabled {
			cursor: default;
			color: #909bd4;
		}

		.file-row span {
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
		}

		.empty {
			color: #909bd4;
			padding: 16px 4px;
		}

		.preview-top {
			display: flex;
			justify-content: space-between;
			gap: 16px;
			margin-bottom: 12px;
		}

		.current-path {
			color: #909bd4;
			font-size: 13px;
			word-break: break-all;
		}

		.preview-tools {
			display: flex;
			align-items: center;
			gap: 10px;
			margin-bottom: 12px;
			flex-wrap: wrap;
		}

		.type-select {
			width: 120px;
		}

		.limit-input {
			width: 96px;
		}

		.tmdb-id-input {
			width: 180px;
		}

		.season-input {
			width: 88px;
		}

		.tip-text {
			color: #909bd4;
			font-size: 13px;
		}

		.preview-summary {
			display: flex;
			gap: 14px;
			margin-bottom: 10px;
			color: #909bd4;
		}

		.conflict-text {
			color: #f56c6c;
		}

		.root-renames {
			margin-bottom: 10px;
			padding: 8px;
			background-color: rgba(64, 158, 255, .08);
			border-radius: 3px;
		}

		.root-rename-item {
			font-size: 12px;
			line-height: 18px;
			word-break: break-all;
		}

		.root-rename-item + .root-rename-item {
			margin-top: 6px;
		}

		.preview-table {
			width: 100%;
			flex: 1;
		}

		.path-cell {
			word-break: break-all;
			line-height: 18px;
		}

		.path-cell.changed {
			color: #67c23a;
		}

		.path-cell.conflict {
			color: #f56c6c;
		}

		.stderr {
			color: #f56c6c;
		}

		.tmdb-search-mask {
			position: fixed;
			inset: 0;
			z-index: 4000;
			background-color: rgba(0, 0, 0, .68);
			display: flex;
			justify-content: center;
			align-items: flex-start;
			padding-top: 18vh;
			box-sizing: border-box;
		}

		.tmdb-search-panel {
			width: min(760px, calc(100vw - 40px));
			max-height: 72vh;
			background-color: #1d1f2c;
			border-radius: 8px;
			box-shadow: 0 18px 60px rgba(0, 0, 0, .45);
			overflow: hidden;
			display: flex;
			flex-direction: column;
		}

		.tmdb-search-bar {
			height: 66px;
			display: flex;
			align-items: center;
			gap: 12px;
			padding: 0 18px;
			border-bottom: 1px solid rgba(255, 255, 255, .1);
			box-sizing: border-box;
		}

		.tmdb-search-input {
			flex: 1;
			min-width: 0;
			height: 100%;
			border: 0;
			outline: 0;
			background: transparent;
			color: #eef0ff;
			font-size: 20px;
			letter-spacing: 0;
		}

		.tmdb-search-input::placeholder {
			color: #909399;
		}

		.tmdb-search-submit,
		.tmdb-search-close {
			width: 38px;
			height: 38px;
			border: 0;
			padding: 0;
			background: transparent;
			color: #a8acc4;
			cursor: pointer;
			font-size: 26px;
			display: flex;
			align-items: center;
			justify-content: center;
		}

		.tmdb-search-submit:hover,
		.tmdb-search-close:hover {
			color: #fff;
		}

		.tmdb-result-list {
			min-height: 220px;
			max-height: calc(72vh - 66px);
			overflow: auto;
			padding: 10px 12px 14px;
			box-sizing: border-box;
		}

		.tmdb-result-item {
			display: flex;
			gap: 14px;
			padding: 14px 6px;
			cursor: pointer;
			border-bottom: 1px solid rgba(255, 255, 255, .08);
		}

		.tmdb-result-item:hover {
			background-color: rgba(64, 158, 255, .12);
		}

		.tmdb-poster {
			width: 62px;
			height: 92px;
			flex: 0 0 62px;
			border-radius: 3px;
			overflow: hidden;
			background-color: rgba(255, 255, 255, .06);
			display: flex;
			align-items: center;
			justify-content: center;
			color: #909bd4;
			font-size: 22px;
		}

		.tmdb-poster img {
			width: 100%;
			height: 100%;
			object-fit: cover;
			display: block;
		}

		.tmdb-info {
			min-width: 0;
			flex: 1;
		}

		.tmdb-title {
			display: flex;
			align-items: center;
			gap: 8px;
			font-size: 16px;
			line-height: 22px;
			margin-bottom: 4px;
			flex-wrap: wrap;
		}

		.tmdb-type {
			margin-left: 4px;
		}

		.tmdb-id,
		.tmdb-original {
			color: #909bd4;
			font-size: 12px;
		}

		.tmdb-overview {
			color: #d6dcff;
			line-height: 20px;
			display: -webkit-box;
			-webkit-line-clamp: 3;
			-webkit-box-orient: vertical;
			overflow: hidden;
		}
	}
</style>
