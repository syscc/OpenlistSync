<template>
	<div class="media-scraping-page">
		<div class="page-title">{{ $t('mediaScraping.title') }}</div>
		<div class="workbench">
			<div class="panel browser-panel">
				<div class="panel-title">{{ $t('mediaScraping.mediaPath') }}</div>
				<div class="default-engine">
					<div>
						<div class="engine-label">{{ $t('mediaScraping.defaultEngine') }}</div>
						<div class="engine-name">{{selectedEngineName}}</div>
					</div>
					<el-button size="small" @click="toScrapingConfig">{{ $t('mediaScraping.scrapingConfig') }}</el-button>
				</div>
				<div class="path-bar">
						<el-input v-model="currentPath" size="small" :placeholder="$t('mediaScraping.pathPlaceholder')" @keyup.enter="browsePath(currentPath)">
							<template #append>
								<el-button @click="browsePath(currentPath)">{{ $t('mediaScraping.jump') }}</el-button>
							</template>
					</el-input>
				</div>
				<div class="browser-actions">
						<el-button size="small" @click="goParent">{{ $t('mediaScraping.parent') }}</el-button>
						<el-button size="small" :loading="browseLoading" :title="$t('mediaScraping.forceRefreshTitle')"
						@click="browsePath(currentPath, true)">{{ $t('mediaScraping.refresh') }}</el-button>
				</div>
				<div class="file-list" v-loading="browseLoading">
					<div class="file-row" v-for="item in browserItems" :key="item.path" :class="{disabled: !item.isDir}"
						@click="item.isDir && browsePath(item.path)">
							<el-icon><component :is="item.isDir ? 'Folder' : 'Document'" /></el-icon>
						<span>{{item.name}}</span>
					</div>
					<div v-if="browserItems.length === 0 && !browseLoading" class="empty">{{ $t('mediaScraping.emptyContent') }}</div>
				</div>
			</div>

			<div class="panel preview-panel">
				<div class="preview-top">
					<div>
						<div class="panel-title">{{ $t('mediaScraping.namingPreview') }}</div>
						<div class="current-path">{{currentPath}}</div>
					</div>
				</div>
				<div class="preview-tools">
					<el-select v-model="mediaType" size="small" class="type-select" @change="clearPreview">
						<el-option :label="$t('mediaScraping.autoIdentify')" value="auto"></el-option>
						<el-option :label="$t('mediaScraping.movie')" value="movie"></el-option>
						<el-option :label="$t('mediaScraping.tv')" value="tv"></el-option>
					</el-select>
					<el-checkbox v-model="recursive" @change="clearPreview">{{ $t('mediaScraping.recursive') }}</el-checkbox>
					<el-input-number v-model="config.limit" size="small" :min="0" controls-position="right" class="limit-input"
						@change="clearPreview"></el-input-number>
					<span class="tip-text">{{ $t('mediaScraping.itemLimit') }}</span>
					<el-input v-model="tmdbId" size="small" class="tmdb-id-input" placeholder="TMDb ID" clearable
						@input="clearPreview">
							<template #append>
								<el-button :title="$t('mediaScraping.searchTmdb')" @click="openTmdbSearch">{{ $t('mediaScraping.search') }}</el-button>
							</template>
					</el-input>
					<el-input v-model="seasonNumber" size="small" class="season-input" :placeholder="$t('mediaScraping.season')" clearable
						:disabled="mediaType === 'movie'" @input="clearPreview"></el-input>
					<span class="tip-text">{{ $t('mediaScraping.season') }}</span>
					<el-button type="primary" size="small" :loading="previewLoading"
						:disabled="normalizePath(currentPath) === '/'"
						@click="previewNaming">
						{{ $t('mediaScraping.preview') }}
					</el-button>
					<el-button type="danger" size="small" :loading="runLoading" :disabled="previewLoading || previewItems.length === 0"
						@click="applyNaming">
						{{ $t('mediaScraping.apply') }}
					</el-button>
				</div>

				<div v-if="previewResult" class="preview-summary">
					<span>{{ $t('mediaScraping.previewFiles', { count: previewResult.total }) }}</span>
					<span>{{ $t('mediaScraping.previewChanged', { count: previewResult.changed }) }}</span>
					<span v-if="previewResult.duplicateTargets" class="conflict-text">{{ $t('mediaScraping.targetConflicts', { count: previewResult.duplicateTargets }) }}</span>
					<span v-if="previewResult.limited">{{ $t('mediaScraping.previewLimited', { count: previewResult.previewLimit }) }}</span>
					<span v-if="previewResult.rootRenames && previewResult.rootRenames.length">{{ $t('mediaScraping.rootRenames', { count: previewResult.rootRenames.length }) }}</span>
				</div>
				<div v-if="previewResult && previewResult.rootRenames && previewResult.rootRenames.length" class="root-renames">
					<div v-for="item in previewResult.rootRenames" :key="item.from + item.to" class="root-rename-item">
						<div>{{item.from}}</div>
						<div>{{item.to}}</div>
					</div>
				</div>
					<el-table :data="previewItems" size="small" class="preview-table" height="430" :empty-text="$t('mediaScraping.previewEmpty')">
					<el-table-column :label="$t('mediaScraping.sourcePath')" min-width="280">
							<template #default="scope">
							<div class="path-cell">{{scope.row.srcPath}}</div>
						</template>
					</el-table-column>
					<el-table-column :label="$t('mediaScraping.renamedPath')" min-width="280">
							<template #default="scope">
							<div class="path-cell" :class="{changed: scope.row.changed, conflict: scope.row.duplicateTarget}">
								{{scope.row.targetPath}}
									<el-tag v-if="scope.row.duplicateTarget" size="small" type="danger">{{ $t('mediaScraping.targetConflicts', { count: scope.row.targetConflictCount }) }}</el-tag>
							</div>
						</template>
					</el-table-column>
				</el-table>

			</div>

		</div>
		<div class="panel task-log-panel">
			<div class="log-top">
				<div>
					<div class="panel-title">{{ $t('mediaScraping.renameTasks') }}</div>
					<div class="current-path">{{ $t('mediaScraping.groupHint') }}</div>
				</div>
				<el-button size="small" :loading="taskLoading" @click="getTaskList">{{ $t('mediaScraping.refresh') }}</el-button>
			</div>
				<el-table :data="taskData.taskList" size="small" class="task-table" height="260" :empty-text="$t('mediaScraping.noRenameTasks')"
				v-loading="taskLoading">
				<el-table-column :label="$t('mediaScraping.status')" width="90">
						<template #default="scope">
							<el-tag size="small" :type="taskStatusTag(scope.row.status)">{{taskStatusText(scope.row.status)}}</el-tag>
					</template>
				</el-table-column>
				<el-table-column :label="$t('mediaScraping.task')" min-width="180">
						<template #default="scope">
						<div class="path-cell">{{displayTaskName(scope.row)}}</div>
					</template>
				</el-table-column>
				<el-table-column :label="$t('mediaScraping.path')" min-width="260">
						<template #default="scope">
						<div class="path-cell">{{displayTaskPath(scope.row)}}</div>
					</template>
				</el-table-column>
				<el-table-column :label="$t('mediaScraping.elapsed')" width="90">
						<template #default="scope">{{formatElapsed(scope.row.elapsed)}}</template>
				</el-table-column>
				<el-table-column :label="$t('mediaScraping.stats')" width="190">
						<template #default="scope">
						<span class="log-count">{{ $t('mediaScraping.totalShort') }} {{scope.row.total || 0}}</span>
						<span class="log-count ok">{{ $t('mediaScraping.successShort') }} {{scope.row.successNum || 0}}</span>
						<span class="log-count skip">{{ $t('mediaScraping.skippedShort') }} {{scope.row.skipNum || 0}}</span>
						<span class="log-count fail">{{ $t('mediaScraping.failedShort') }} {{scope.row.failNum || 0}}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('mediaScraping.time')" width="150">
						<template #default="scope">{{timeStampFilter(scope.row.updateTime || scope.row.createTime)}}</template>
				</el-table-column>
				<el-table-column :label="$t('common.operate')" width="250">
						<template #default="scope">
							<el-button size="small" type="primary" @click="manualRunTask(scope.row)"
							:loading="taskActionLoading">{{ $t('mediaScraping.manualRun') }}</el-button>
							<el-button size="small" type="primary" @click="detailTask(scope.row)">{{ $t('mediaScraping.detail') }}</el-button>
							<el-button size="small" type="danger" @click="deleteTask(scope.row)">{{ $t('common.delete') }}</el-button>
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
					<button class="tmdb-search-submit" type="button" :title="$t('mediaScraping.search')" @click="searchTmdb">
							<el-icon><Search /></el-icon>
					</button>
					<input ref="tmdbSearchInput" v-model="tmdbSearchKeyword" class="tmdb-search-input" type="text"
						:placeholder="$t('mediaScraping.searchPlaceholder')" @keydown.enter.prevent="searchTmdb">
					<button class="tmdb-search-close" type="button" :title="$t('mediaScraping.close')" @click="closeTmdbSearch">
							<el-icon><Close /></el-icon>
					</button>
				</div>
				<div class="tmdb-result-list" v-loading="tmdbSearchLoading">
					<div v-for="item in tmdbSearchResults" :key="item.type + '-' + item.id" class="tmdb-result-item"
						@click="selectTmdbResult(item)">
						<div class="tmdb-poster">
							<img v-if="item.posterUrl" :src="item.posterUrl" :alt="item.title">
								<el-icon v-else><Picture /></el-icon>
						</div>
						<div class="tmdb-info">
							<div class="tmdb-title">
								<span>{{item.title}}</span>
								<span v-if="item.year">({{item.year}})</span>
									<el-tag size="small" effect="dark" class="tmdb-type">{{mediaTypeText(item.type)}}</el-tag>
								<span class="tmdb-id">ID {{item.id}}</span>
							</div>
							<div v-if="item.originalTitle && item.originalTitle !== item.title" class="tmdb-original">{{item.originalTitle}}</div>
							<div class="tmdb-overview">{{item.overview || $t('mediaScraping.noOverview')}}</div>
						</div>
					</div>
					<div v-if="tmdbSearchResults.length === 0 && tmdbSearched && !tmdbSearchLoading" class="empty">{{ $t('mediaScraping.noResults') }}</div>
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
				initialBrowseRequested: false,
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
					return this.$t('mediaScraping.unconfigured');
				}
				return engine.remark || engine.url;
			}
		},
		created() {
			Promise.allSettled([this.getOpenlistList(), this.getConfig()]).then(() => {
				this.ensureDefaultEngine();
			});
		},
		beforeUnmount() {},
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
				return openlistGet().then(res => {
					this.openlistList = res.data || [];
				})
			},
			getConfig() {
				return getMediaScrapingConfig().then(res => {
					this.config = Object.assign(this.defaultConfig(), res.data || {});
					this.extensionsText = (this.config.mediaExtensions || []).join(',');
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
				if (this.config.defaultOpenlistId && !this.initialBrowseRequested) {
					this.initialBrowseRequested = true;
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
					this.$message.error(this.$t('mediaScraping.requireEngine'));
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
					this.$message.error(this.$t('mediaScraping.requireSearchKeyword'));
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
			mediaTypeText(type) {
				return this.$t(type === 'tv' ? 'mediaScraping.tv' : 'mediaScraping.movie');
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
				this.$confirm(this.$t('mediaScraping.applyConfirm'), this.$t('mediaScraping.applyConfirmTitle'), {
					confirmButtonText: this.$t('mediaScraping.applyButton'),
					cancelButtonText: this.$t('common.cancel'),
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
								message: this.$t('mediaScraping.runQueued'),
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
				this.$confirm(this.$t('mediaScraping.deleteJobConfirm'), this.$t('common.tips'), {
					confirmButtonText: this.$t('common.confirm'),
					cancelButtonText: this.$t('common.cancel'),
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
						message: this.$t('mediaScraping.rerunQueued'),
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
			color: var(--text-primary);
		}

		.workbench {
			display: grid;
			grid-template-columns: 320px minmax(520px, 1fr);
			gap: 14px;
			align-items: stretch;
			height: 572px;
		}

		.panel {
			background-color: var(--home-item-background-color);
			border: 1px solid var(--border-color);
			border-radius: 6px;
			padding: 16px;
			box-sizing: border-box;
			min-height: 160px;
			min-width: 0;
		}

		.panel-title {
			font-size: 16px;
			font-weight: bold;
			margin-bottom: 12px;
			color: var(--text-primary);
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
			color: var(--text-muted);
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
			background-color: var(--home-background-color);
			border-radius: 4px;
		}

		.engine-label {
			color: var(--text-muted);
			font-size: 12px;
			margin-bottom: 4px;
		}

		.engine-name {
			max-width: 190px;
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
			color: var(--text-primary);
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
			border-top: 1px solid var(--border-color);
		}

		.file-row {
			height: 34px;
			display: flex;
			align-items: center;
			gap: 8px;
			padding: 0 4px;
			cursor: pointer;
			border-bottom: 1px solid var(--border-color);
			color: var(--text-primary);
		}

		.file-row:hover {
			background-color: rgba(64, 158, 255, .12);
		}

		.file-row.disabled {
			cursor: default;
			color: var(--text-muted);
		}

		.file-row span {
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
		}

		.empty {
			color: var(--text-muted);
			padding: 16px 4px;
		}

		.preview-top {
			display: flex;
			justify-content: space-between;
			gap: 16px;
			margin-bottom: 12px;
		}

		.current-path {
			color: var(--text-muted);
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
			color: var(--text-muted);
			font-size: 13px;
		}

		.preview-summary {
			display: flex;
			gap: 14px;
			margin-bottom: 10px;
			color: var(--text-muted);
			flex-wrap: wrap;
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
			background-color: var(--home-item-background-color);
			border: 1px solid var(--border-color);
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
			border-bottom: 1px solid var(--border-color);
			box-sizing: border-box;
		}

		.tmdb-search-input {
			flex: 1;
			min-width: 0;
			height: 100%;
			border: 0;
			outline: 0;
			background: transparent;
			color: var(--text-primary);
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
			color: var(--text-secondary);
			cursor: pointer;
			font-size: 26px;
			display: flex;
			align-items: center;
			justify-content: center;
		}

		.tmdb-search-submit:hover,
		.tmdb-search-close:hover {
			color: var(--active-color);
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
			border-bottom: 1px solid var(--border-color);
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
			background-color: var(--home-background-color);
			display: flex;
			align-items: center;
			justify-content: center;
			color: var(--text-muted);
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
			color: var(--text-primary);
		}

		.tmdb-type {
			margin-left: 4px;
		}

		.tmdb-id,
		.tmdb-original {
			color: var(--text-muted);
			font-size: 12px;
		}

		.tmdb-overview {
			color: var(--text-secondary);
			line-height: 20px;
			display: -webkit-box;
			-webkit-line-clamp: 3;
			-webkit-box-orient: vertical;
			overflow: hidden;
		}
	}

	@media (max-width: 1180px) {
		.media-scraping-page {
			.workbench {
				grid-template-columns: minmax(0, 1fr);
				height: auto;
			}

			.browser-panel {
				height: 420px;
			}

			.preview-panel {
				height: 620px;
			}
		}
	}

	@media (max-width: 768px) {
		.media-scraping-page {
			padding: 12px 10px 20px;

			.page-title {
				margin-bottom: 12px;
				font-size: 18px;
			}

			.workbench {
				gap: 10px;
			}

			.panel {
				padding: 12px;
			}

			.browser-panel {
				height: 390px;
			}

			.preview-panel {
				height: 660px;
			}

			.default-engine > div {
				min-width: 0;
			}

			.engine-name {
				max-width: none;
			}

			.preview-tools {
				gap: 8px;
			}

			.type-select {
				width: 142px;
			}

			.tmdb-id-input {
				width: 100%;
			}

			.preview-tools > .el-button {
				flex: 1 1 calc(50% - 4px);
				margin-left: 0;
			}

			.task-log-panel {
				margin-top: 10px;
			}

			.log-top {
				align-items: center;
			}

			.page-line {
				justify-content: center;
				overflow-x: auto;
			}

			.tmdb-search-mask {
				align-items: center;
				padding: 16px 10px;
			}

			.tmdb-search-panel {
				width: 100%;
				max-height: calc(100dvh - 32px);
			}

			.tmdb-search-bar {
				height: 56px;
				gap: 8px;
				padding: 0 10px;
			}

			.tmdb-search-input {
				font-size: 16px;
			}

			.tmdb-result-list {
				max-height: calc(100dvh - 90px);
				padding: 6px 8px 10px;
			}

			.tmdb-result-item {
				gap: 10px;
				padding: 12px 4px;
			}

			.tmdb-poster {
				width: 54px;
				height: 80px;
				flex-basis: 54px;
			}
		}
	}
</style>
