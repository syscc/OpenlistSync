<template>
	<div class="media-scraping-page">
		<div class="page-heading">
			<div class="page-heading-icon" aria-hidden="true"><Clapperboard /></div>
			<div class="page-title">{{ $t('mediaScraping.title') }}</div>
		</div>
		<nav class="mobile-workbench-nav" :aria-label="$t('mediaScraping.title')">
			<button type="button" :class="{active: activeMobileSection === 'browser'}"
				:aria-current="activeMobileSection === 'browser' ? 'location' : undefined"
				@click="scrollToWorkbench('browser')">
				<Folder aria-hidden="true" />
				<span>{{ $t('mediaScraping.mediaPath') }}</span>
			</button>
			<button type="button" :class="{active: activeMobileSection === 'preview'}"
				:aria-current="activeMobileSection === 'preview' ? 'location' : undefined"
				@click="scrollToWorkbench('preview')">
				<Eye aria-hidden="true" />
				<span>{{ $t('mediaScraping.namingPreview') }}</span>
			</button>
			<button type="button" :class="{active: activeMobileSection === 'tasks'}"
				:aria-current="activeMobileSection === 'tasks' ? 'location' : undefined"
				@click="scrollToWorkbench('tasks')">
				<ListChecks aria-hidden="true" />
				<span>{{ $t('mediaScraping.renameTasks') }}</span>
			</button>
		</nav>
		<div class="workbench">
			<div ref="browserPanel" class="panel browser-panel">
				<div class="panel-title">{{ $t('mediaScraping.mediaPath') }}</div>
				<div class="default-engine">
					<div>
						<div class="engine-label">{{ $t('mediaScraping.defaultEngine') }}</div>
						<div class="engine-name">{{selectedEngineName}}</div>
					</div>
					<el-button size="small" @click="toScrapingConfig">
						<Settings2 aria-hidden="true" />
						<span>{{ $t('mediaScraping.scrapingConfig') }}</span>
					</el-button>
				</div>
				<div class="path-bar">
						<el-input v-model="currentPath" size="small" :placeholder="$t('mediaScraping.pathPlaceholder')" @keyup.enter="browsePath(currentPath)">
							<template #append>
								<el-button @click="browsePath(currentPath)">
									<ArrowRight aria-hidden="true" />
									<span>{{ $t('mediaScraping.jump') }}</span>
								</el-button>
							</template>
					</el-input>
				</div>
				<div class="browser-actions">
						<el-button size="small" @click="goParent">
							<ArrowUp aria-hidden="true" />
							<span>{{ $t('mediaScraping.parent') }}</span>
						</el-button>
						<el-button size="small" :loading="browseLoading" :title="$t('mediaScraping.forceRefreshTitle')"
						@click="browsePath(currentPath, true)">
							<RefreshCw aria-hidden="true" />
							<span>{{ $t('mediaScraping.refresh') }}</span>
						</el-button>
				</div>
				<div class="file-list" v-loading="browseLoading">
					<div class="file-row" v-for="item in browserItems" :key="item.path"
						:class="{disabled: !item.isDir && !isMediaFile(item), selected: !item.isDir && selectedFilePath === item.path}"
						role="button" :tabindex="isBrowserItemActionable(item) ? 0 : -1"
						:aria-disabled="!isBrowserItemActionable(item)" :aria-pressed="item.isDir ? undefined : selectedFilePath === item.path"
						@click="selectBrowserItem(item)" @keydown.enter.prevent="selectBrowserItem(item)"
						@keydown.space.prevent="selectBrowserItem(item)">
							<Folder v-if="item.isDir" aria-hidden="true" />
							<File v-else aria-hidden="true" />
						<span>{{item.name}}</span>
					</div>
					<div v-if="browserItems.length === 0 && !browseLoading" class="empty">{{ $t('mediaScraping.emptyContent') }}</div>
				</div>
			</div>

			<div ref="previewPanel" class="panel preview-panel">
				<div class="preview-top">
					<div>
						<div class="panel-title">{{ $t('mediaScraping.namingPreview') }}</div>
						<div class="current-path">{{previewPath}}</div>
					</div>
				</div>
				<div class="preview-tools">
					<el-select v-model="mediaType" size="small" class="type-select" @change="clearPreview">
						<el-option :label="$t('mediaScraping.autoIdentify')" value="auto"></el-option>
						<el-option :label="$t('mediaScraping.movie')" value="movie"></el-option>
						<el-option :label="$t('mediaScraping.tv')" value="tv"></el-option>
					</el-select>
					<el-checkbox v-model="recursive" :disabled="singleFileMode" @change="clearPreview">{{ $t('mediaScraping.recursive') }}</el-checkbox>
					<el-input-number v-model="config.limit" size="small" :min="0" controls-position="right" class="limit-input"
						@change="clearPreview"></el-input-number>
					<span class="tip-text">{{ $t('mediaScraping.itemLimit') }}</span>
					<el-input v-model="tmdbId" size="small" class="tmdb-id-input" placeholder="TMDb ID" clearable
						@input="clearPreview">
							<template #append>
								<el-button :title="$t('mediaScraping.searchTmdb')" @click="openTmdbSearch">
									<SearchIcon aria-hidden="true" />
									<span>{{ $t('mediaScraping.search') }}</span>
								</el-button>
							</template>
					</el-input>
					<el-input v-model="seasonNumber" size="small" class="season-input" :placeholder="$t('mediaScraping.season')" clearable
						:disabled="mediaType === 'movie'" @input="clearPreview"></el-input>
					<span class="tip-text">{{ $t('mediaScraping.season') }}</span>
					<el-button type="primary" size="small" :loading="previewLoading"
						:disabled="normalizePath(previewPath) === '/'"
						@click="previewNaming">
						<Eye aria-hidden="true" />
						<span>{{ $t('mediaScraping.preview') }}</span>
					</el-button>
					<el-button type="danger" size="small" :loading="runLoading" :disabled="previewLoading || previewItems.length === 0"
						@click="applyNaming">
						<Play aria-hidden="true" />
						<span>{{ $t('mediaScraping.apply') }}</span>
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
		<div ref="tasksPanel" class="panel task-log-panel">
			<div class="log-top">
				<div>
					<div class="panel-title">{{ $t('mediaScraping.renameTasks') }}</div>
					<div class="current-path">{{ $t('mediaScraping.groupHint') }}</div>
				</div>
				<el-button size="small" :loading="taskLoading" @click="getTaskList">
					<RefreshCw aria-hidden="true" />
					<span>{{ $t('mediaScraping.refresh') }}</span>
				</el-button>
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
							:loading="taskActionLoading">
								<RotateCcw aria-hidden="true" />
								<span>{{ $t('mediaScraping.manualRun') }}</span>
							</el-button>
							<el-button size="small" @click="detailTask(scope.row)">
								<Eye aria-hidden="true" />
								<span>{{ $t('mediaScraping.detail') }}</span>
							</el-button>
							<el-button size="small" type="danger" plain @click="deleteTask(scope.row)">
								<Trash2 aria-hidden="true" />
								<span>{{ $t('common.delete') }}</span>
							</el-button>
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
		<el-dialog v-model="tmdbSearchVisible" class="tmdb-search-dialog" :title="$t('mediaScraping.searchTmdb')"
			width="min(760px, calc(100vw - 32px))" align-center destroy-on-close @opened="focusTmdbSearch">
			<div class="tmdb-search-bar">
				<el-input ref="tmdbSearchInput" v-model="tmdbSearchKeyword" size="large"
					:placeholder="$t('mediaScraping.searchPlaceholder')" @keyup.enter="searchTmdb">
					<template #prefix><SearchIcon aria-hidden="true" /></template>
					<template #append>
						<el-button :loading="tmdbSearchLoading" @click="searchTmdb">
							<SearchIcon aria-hidden="true" />
							<span>{{ $t('mediaScraping.search') }}</span>
						</el-button>
					</template>
				</el-input>
			</div>
				<div class="tmdb-result-list" v-loading="tmdbSearchLoading">
					<button v-for="item in tmdbSearchResults" :key="item.type + '-' + item.id" type="button" class="tmdb-result-item"
						@click="selectTmdbResult(item)">
						<span class="tmdb-poster">
							<img v-if="item.posterUrl" :src="item.posterUrl" :alt="item.title">
							<ImageIcon v-else aria-hidden="true" />
						</span>
						<span class="tmdb-info">
							<span class="tmdb-title">
								<span>{{item.title}}</span>
								<span v-if="item.year">({{item.year}})</span>
									<el-tag size="small" effect="dark" class="tmdb-type">{{mediaTypeText(item.type)}}</el-tag>
								<span class="tmdb-id">ID {{item.id}}</span>
							</span>
							<span v-if="item.originalTitle && item.originalTitle !== item.title" class="tmdb-original">{{item.originalTitle}}</span>
							<span class="tmdb-overview">{{item.overview || $t('mediaScraping.noOverview')}}</span>
						</span>
					</button>
					<div v-if="tmdbSearchResults.length === 0 && tmdbSearched && !tmdbSearchLoading" class="empty">{{ $t('mediaScraping.noResults') }}</div>
				</div>
		</el-dialog>
	</div>
</template>

<script>
	import {
		ArrowRight,
		ArrowUp,
		Clapperboard,
		Eye,
		File,
		Folder,
		Image as ImageIcon,
		ListChecks,
		Play,
		RefreshCw,
		RotateCcw,
		Search as SearchIcon,
		Settings2,
		Trash2
	} from "@lucide/vue";
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
		components: {
			ArrowRight,
			ArrowUp,
			Clapperboard,
			Eye,
			File,
			Folder,
			ImageIcon,
			ListChecks,
			Play,
			RefreshCw,
			RotateCcw,
			SearchIcon,
			Settings2,
			Trash2
		},
		data() {
			return {
				openlistList: [],
				config: this.defaultConfig(),
				extensionsText: '',
				currentPath: '/',
				selectedFilePath: '',
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
				tmdbSearched: false,
				activeMobileSection: 'browser',
				mobileScrollContainer: null,
				mobileScrollFrame: 0
			};
		},
		computed: {
			previewPath() {
				return this.selectedFilePath || this.currentPath;
			},
			singleFileMode() {
				return Boolean(this.selectedFilePath);
			},
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
		mounted() {
			this.mobileScrollContainer = this.$el.closest('.app-main');
			this.mobileScrollContainer?.addEventListener('scroll', this.scheduleMobileSectionUpdate, { passive: true });
			window.addEventListener('resize', this.scheduleMobileSectionUpdate, { passive: true });
			this.$nextTick(this.updateActiveMobileSection);
		},
		beforeUnmount() {
			this.mobileScrollContainer?.removeEventListener('scroll', this.scheduleMobileSectionUpdate);
			window.removeEventListener('resize', this.scheduleMobileSectionUpdate);
			if (this.mobileScrollFrame) {
				cancelAnimationFrame(this.mobileScrollFrame);
			}
		},
		methods: {
			scheduleMobileSectionUpdate() {
				if (this.mobileScrollFrame) return;
				this.mobileScrollFrame = requestAnimationFrame(() => {
					this.mobileScrollFrame = 0;
					this.updateActiveMobileSection();
				});
			},
			updateActiveMobileSection() {
				if (!window.matchMedia('(max-width: 768px)').matches) return;
				const container = this.mobileScrollContainer;
				if (!container) return;

				if (container.scrollTop + container.clientHeight >= container.scrollHeight - 2) {
					this.activeMobileSection = 'tasks';
					return;
				}

				const sections = [
					['browser', this.$refs.browserPanel],
					['preview', this.$refs.previewPanel],
					['tasks', this.$refs.tasksPanel]
				];
				let active = 'browser';
				for (const [name, panel] of sections) {
					if (panel && panel.getBoundingClientRect().top <= 112) {
						active = name;
					}
				}
				this.activeMobileSection = active;
			},
			scrollToWorkbench(section) {
				const refMap = {
					browser: 'browserPanel',
					preview: 'previewPanel',
					tasks: 'tasksPanel'
				};
				this.activeMobileSection = section;
				const target = this.$refs[refMap[section]];
				if (target) {
					target.scrollIntoView({ behavior: 'smooth', block: 'start' });
				}
			},
			defaultConfig() {
					return {
						defaultOpenlistId: null,
						openlistIds: [],
						tmdbApiKey: '',
						tmdbBearerToken: '',
						tmdbApiUrl: 'https://api.themoviedb.org',
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
				this.selectedFilePath = '';
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
			isMediaFile(item) {
				if (!item || item.isDir) {
					return false;
				}
				const name = String(item.name || '').toLowerCase();
				return (this.config.mediaExtensions || []).some(extension => {
					const normalized = String(extension || '').trim().toLowerCase();
					return normalized && name.endsWith(normalized.startsWith('.') ? normalized : `.${normalized}`);
				});
			},
			isBrowserItemActionable(item) {
				return Boolean(item && (item.isDir || this.isMediaFile(item)));
			},
			selectBrowserItem(item) {
				if (item && item.isDir) {
					this.browsePath(item.path);
					return;
				}
				if (!this.isMediaFile(item)) {
					return;
				}
				this.selectedFilePath = item.path;
				this.clearPreview();
			},
			clearPreview() {
				this.previewSeq += 1;
				this.previewLoading = false;
				this.previewResult = null;
			},
			defaultSearchKeyword() {
				const parts = this.normalizePath(this.previewPath).split('/').filter(item => item);
				const name = parts.length ? parts[parts.length - 1] : '';
				return name
					.replace(/\.[^.]+$/, '')
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
			},
			focusTmdbSearch() {
				const input = this.$refs.tmdbSearchInput;
				if (input) {
					input.focus();
					if (input.input) {
						input.input.select();
					}
				}
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
				if (this.normalizePath(this.previewPath) === '/') {
					this.previewResult = null;
					return;
				}
				const requestSeq = ++this.previewSeq;
				this.previewLoading = true;
				previewMediaScraping({
					openlistId: this.config.defaultOpenlistId,
					path: this.previewPath,
					type: this.mediaType,
					recursive: this.singleFileMode ? false : this.recursive,
					singleFile: this.singleFileMode,
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
						path: this.previewPath,
						type: this.mediaType,
						recursive: this.singleFileMode ? false : this.recursive,
						singleFile: this.singleFileMode,
						tmdbId: this.tmdbId,
						seasonNumber: this.seasonNumber
					}];
					runMediaScraping({
						apply: true,
						path: this.previewPath,
						type: this.mediaType,
						recursive: this.singleFileMode ? false : this.recursive,
						singleFile: this.singleFileMode,
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
		height: 100%;
		min-height: 680px;
		box-sizing: border-box;
		display: grid;
		grid-template-rows: auto minmax(0, 3fr) minmax(0, 2fr);
		gap: 12px;
		color: var(--text-primary);

		.page-heading {
			display: flex;
			align-items: center;
			gap: 10px;
			min-height: 32px;
		}

		.page-heading-icon {
			width: 32px;
			height: 32px;
			border: 1px solid color-mix(in srgb, var(--active-color) 24%, transparent);
				border-radius: 8px;
			background: var(--brand-soft);
			color: var(--active-color);
			display: grid;
			place-items: center;
		}

		.page-heading-icon svg {
			width: 17px;
			height: 17px;
			stroke-width: 1.8;
		}

		.page-title {
			font-size: 20px;
			font-weight: 700;
				letter-spacing: 0;
			margin-bottom: 4px;
			color: var(--text-primary);
		}

		.mobile-workbench-nav {
			display: none;
		}

		.workbench {
			display: grid;
			grid-template-columns: 320px minmax(520px, 1fr);
			gap: 14px;
			align-items: stretch;
			height: auto;
			min-height: 0;
		}

		.panel {
			position: relative;
			background: var(--home-item-background-color);
			border: 1px solid var(--border-color);
			border-radius: 8px;
			padding: 16px;
			box-sizing: border-box;
			min-height: 160px;
			min-width: 0;
			box-shadow: 0 10px 30px rgba(15, 23, 42, .045);
		}

		.panel-title {
			font-size: 15px;
			font-weight: 700;
				letter-spacing: 0;
			margin-bottom: 12px;
			color: var(--text-primary);
		}

		.task-log-panel {
			margin-top: 0;
			display: flex;
			flex-direction: column;
			min-height: 0;
			overflow: hidden;
		}

		.task-table {
			flex: 1;
			min-height: 0;
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
			color: var(--success-color);
		}

		.log-count.skip {
			color: var(--text-muted);
		}

		.log-count.fail {
			color: var(--fail-color);
		}

		.default-engine {
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: 10px;
			padding: 11px 12px;
			background-color: var(--home-background-color);
			border: 1px solid color-mix(in srgb, var(--border-color) 72%, transparent);
				border-radius: 8px;
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
			border: 1px solid var(--border-color);
				border-radius: 8px;
		}

		.file-row {
			min-height: 38px;
			display: flex;
			align-items: center;
			gap: 8px;
			padding: 0 10px;
			cursor: pointer;
			border-bottom: 1px solid var(--border-color);
			color: var(--text-primary);
			transition: background-color .16s ease, color .16s ease, box-shadow .16s ease;
		}

		.file-row:hover:not(.disabled) {
			background-color: var(--surface-hover);
		}

		.file-row:focus-visible,
		.tmdb-result-item:focus-visible,
		.mobile-workbench-nav button:focus-visible {
			outline: 2px solid var(--active-color);
			outline-offset: -2px;
		}

		.file-row svg {
			width: 17px;
			height: 17px;
			flex: none;
			stroke-width: 1.7;
			color: var(--text-muted);
		}

		.file-row.disabled {
			cursor: default;
			color: var(--text-muted);
		}

		.file-row.selected {
			background-color: var(--brand-soft);
			box-shadow: inset 3px 0 0 var(--el-color-primary);
		}

		.file-row.selected svg {
			color: var(--active-color);
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
			color: var(--fail-color);
		}

		.root-renames {
			max-height: 126px;
			overflow-y: auto;
			margin-bottom: 10px;
			padding: 8px;
			background-color: var(--info-soft);
			border-radius: 8px;
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
			min-height: 0;
		}

		.path-cell {
			word-break: break-all;
			line-height: 18px;
		}

		.path-cell.changed {
			color: var(--success-color);
		}

		.path-cell.conflict {
			color: var(--fail-color);
		}

		.stderr {
			color: var(--fail-color);
		}

		.tmdb-search-bar {
			padding-bottom: 14px;
		}

		.tmdb-search-bar svg {
			width: 17px;
			height: 17px;
		}

		.tmdb-result-list {
			min-height: 220px;
			max-height: min(58vh, 560px);
			overflow: auto;
			padding: 0 2px;
			box-sizing: border-box;
		}

		.tmdb-result-item {
			width: 100%;
			display: flex;
			text-align: left;
			gap: 14px;
			padding: 12px;
			cursor: pointer;
			border: 1px solid transparent;
			border-radius: 8px;
			background: transparent;
			color: inherit;
			font: inherit;
			transition: background-color .16s ease, border-color .16s ease, transform .16s ease;
		}

		.tmdb-result-item:hover {
			background-color: var(--surface-hover);
			border-color: color-mix(in srgb, var(--active-color) 20%, transparent);
			transform: translateY(-1px);
		}

		.tmdb-poster {
			width: 62px;
			height: 92px;
			flex: 0 0 62px;
			border-radius: 8px;
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
			display: block;
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
			display: -webkit-box;
			color: var(--text-secondary);
			line-height: 20px;
			-webkit-line-clamp: 3;
			-webkit-box-orient: vertical;
			overflow: hidden;
		}

		:deep(.el-button > svg) {
			width: 15px;
			height: 15px;
			stroke-width: 1.8;
		}

		:deep(.el-button > svg + span) {
			margin-left: 6px;
		}
	}

	:global(.tmdb-search-dialog) {
		border-radius: 8px;
		overflow: hidden;
		background: var(--home-item-background-color);
		box-shadow: 0 28px 90px rgba(0, 0, 0, .34);
	}

	:global(.tmdb-search-dialog .el-dialog__header) {
		padding: 18px 22px 12px;
		margin-right: 0;
	}

	:global(.tmdb-search-dialog .el-dialog__body) {
		padding: 8px 20px 20px;
	}

	@media (max-width: 1180px) {
		.media-scraping-page {
			height: auto;
			display: block;

			.page-title {
				margin-bottom: 16px;
			}

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

			.task-log-panel {
				display: block;
				margin-top: 12px;
				overflow: visible;
			}

			.task-table {
				flex: none;
				min-height: 260px;
			}
		}
	}

	@media (max-width: 768px) {
		.media-scraping-page {
			padding: 12px 10px 20px;

			.page-heading {
				margin-bottom: 10px;
			}

			.page-title {
				margin-bottom: 0;
				font-size: 18px;
			}

			.mobile-workbench-nav {
				position: sticky;
				top: 54px;
				z-index: 5;
				display: grid;
				grid-template-columns: repeat(3, minmax(0, 1fr));
				gap: 4px;
				margin: 0 0 10px;
				padding: 4px;
				border: 1px solid var(--border-color);
				border-radius: 8px;
				background: color-mix(in srgb, var(--home-item-background-color) 92%, transparent);
				box-shadow: 0 8px 24px rgba(15, 23, 42, .08);
				backdrop-filter: blur(16px);
			}

			.mobile-workbench-nav button {
				min-width: 0;
				height: 38px;
				border: 0;
					border-radius: 8px;
				background: transparent;
				color: var(--text-muted);
				font: inherit;
				font-size: 12px;
				display: flex;
				align-items: center;
				justify-content: center;
				gap: 6px;
				cursor: pointer;
			}

			.mobile-workbench-nav button.active {
				background: var(--brand-soft);
				color: var(--active-color);
			}

			.mobile-workbench-nav svg {
				width: 15px;
				height: 15px;
				flex: none;
			}

			.workbench {
				gap: 10px;
			}

			.panel {
				padding: 12px;
					border-radius: 8px;
				scroll-margin-top: 108px;
			}

			.browser-panel {
				height: min(390px, calc(100dvh - 232px));
				min-height: 300px;
			}

			.preview-panel {
				height: auto;
				min-height: 660px;
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

			.tmdb-search-bar {
				padding-bottom: 10px;
			}

			.tmdb-result-list {
				max-height: calc(100dvh - 190px);
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

		:global(.tmdb-search-dialog .el-dialog__header) {
			padding: 16px 16px 10px;
		}

		:global(.tmdb-search-dialog .el-dialog__body) {
			padding: 6px 12px 14px;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.media-scraping-page {
			.file-row,
			.tmdb-result-item {
				transition: none;
			}

			.tmdb-result-item:hover {
				transform: none;
			}
		}
	}
</style>
