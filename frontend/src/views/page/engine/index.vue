<template>
	<div class="engine">
		<div class="engine-top">
			<el-select v-model="configMode" size="small" class="config-mode">
				<el-option label="OpenList" value="openlist"></el-option>
				<el-option label="刮削配置" value="mediaScraping"></el-option>
			</el-select>
		</div>
		<div class="loading-box content-none-data" v-loading="true" v-if="getLoading && configMode === 'openlist'">加载中</div>
		<div v-else-if="configMode === 'openlist'" class="card-box">
			<div class="card-item" v-for="item in openlistList" :key="item.id">
				<div class="card-item-top">
					<el-image src="/logo/logo.svg" fit="contain" style="width: 60px;height: 60px;"></el-image>
					<div style="margin-left: 12px;">
						<div class="card-item-user">{{item.userName}}
							<div class="card-item-remark" v-if="item.remark != null">[{{item.remark}}]</div>
						</div>
						<div class="card-item-url">{{item.url}}</div>
					</div>
				</div>
				<div class="card-item-bottom">
					<el-button size="small" type="primary" @click="editShowDialog(item)">编辑</el-button>
					<el-button size="small" type="danger" @click="delOpenlist(item.id)">删除</el-button>
				</div>
			</div>
			<div class="card-item card-add" @click="addShow" v-if="!getLoading">
				<template v-if="openlistList.length == 0">
					暂无引擎，请<span style="color: #409eff;">新增</span>
				</template>
				<span v-else>新增</span>
			</div>
			<el-dialog :close-on-click-modal="false" :visible.sync="editShow" :title="editFlag ? '编辑' : '新增'" width="600px"
				:before-close="closeShow" :append-to-body="true">
				<div class="elform-box">
					<el-form :model="editData" :rules="editFlag ? editRule : addRule" ref="addRule" v-if="editShow"
						label-width="66px">
						<el-form-item prop="url" label="地址">
							<el-input v-model="editData.url" placeholder="请输入地址，如http://127.0.0.1:5244"></el-input>
						</el-form-item>
						<el-form-item prop="remark" label="备注">
							<el-input v-model="editData.remark" placeholder="备注方便你标识引擎，非必填"></el-input>
						</el-form-item>
						<el-form-item prop="token" label="令牌">
							<el-input v-model="editData.token" show-password
							:placeholder="`请输入令牌，${editFlag ? '留空表示不修改' : '请到OpenList管理-设置-其他中复制，保存后不要重置令牌'}`"
								@keyup.enter.native="submit"></el-input>
						</el-form-item>
					</el-form>
				</div>
				<span slot="footer" class="dialog-footer">
					<el-button @click="closeShow">取 消</el-button>
					<el-button type="primary" @click="submit" :loading="editLoading">确 定</el-button>
				</span>
			</el-dialog>
		</div>
		<div v-else class="scraping-config">
			<el-form label-width="116px" size="small">
				<div class="config-block">
					<div class="block-title">默认引擎</div>
					<el-form-item label="OpenList">
						<el-select v-model="mediaConfig.defaultOpenlistId" filterable placeholder="选择默认打开的 OpenList 引擎" class="config-width">
							<el-option v-for="item in openlistList" :key="item.id" :label="item.remark || item.url" :value="item.id">
								<span>{{item.remark || item.url}}</span>
								<span class="option-url">{{item.url}}</span>
							</el-option>
						</el-select>
					</el-form-item>
				</div>
				<div class="config-block">
					<div class="block-title">TMDb</div>
					<el-form-item label="API Key">
						<el-input v-model="mediaConfig.tmdbApiKey" class="config-width" show-password></el-input>
					</el-form-item>
					<el-form-item label="Bearer Token">
						<el-input v-model="mediaConfig.tmdbBearerToken" class="config-width" show-password></el-input>
					</el-form-item>
					<el-form-item label="语言">
						<el-input v-model="mediaConfig.tmdbLanguage" class="short-width"></el-input>
					</el-form-item>
					<el-form-item label="匹配选项">
						<el-checkbox v-model="mediaConfig.tmdbRequired">必须配置 TMDb</el-checkbox>
						<el-checkbox v-model="mediaConfig.tmdbIncludeAdult">包含成人内容</el-checkbox>
					</el-form-item>
				</div>
				<div class="config-block">
					<div class="block-title">命名参数</div>
					<el-form-item label="运行选项">
						<el-checkbox v-model="mediaConfig.refresh">刷新目录缓存</el-checkbox>
						<el-checkbox v-model="mediaConfig.overwrite">允许覆盖</el-checkbox>
					</el-form-item>
					<el-form-item label="处理数量">
						<el-input-number v-model="mediaConfig.limit" :min="0"></el-input-number>
						<span class="tip-text">0 表示不限制</span>
					</el-form-item>
					<el-form-item label="改名线程">
						<el-input-number v-model="mediaConfig.renameThreads" :min="1" :max="16"></el-input-number>
						<span class="tip-text">默认 2，根目录仍最后单线程改名</span>
					</el-form-item>
					<el-form-item label="重命名日志">
						<el-input-number v-model="mediaConfig.renameLogLimit" :min="0" :max="1000"></el-input-number>
						<span class="tip-text">保留最近多少次，0 表示不清理</span>
					</el-form-item>
					<el-form-item label="超时">
						<el-input-number v-model="mediaConfig.openlistTimeout" :min="1" :step="5"></el-input-number>
						<span class="tip-text">OpenList 秒</span>
						<el-input-number v-model="mediaConfig.tmdbTimeout" :min="1" :step="5"></el-input-number>
						<span class="tip-text">TMDb 秒</span>
					</el-form-item>
					<el-form-item label="媒体扩展名">
						<el-input v-model="extensionsText" class="config-width" placeholder=".mkv,.mp4,.ts"></el-input>
					</el-form-item>
				</div>
				<div class="config-block">
					<div class="block-title">模板与 MoviePilot</div>
					<el-form-item label="电影模板">
						<el-input v-model="mediaConfig.movieTemplate" type="textarea" :rows="3" class="config-width"></el-input>
					</el-form-item>
					<el-form-item label="电视剧模板">
						<el-input v-model="mediaConfig.tvTemplate" type="textarea" :rows="4" class="config-width"></el-input>
					</el-form-item>
					<el-form-item label="自定义词">
						<el-input v-model="mediaConfig.customWords" type="textarea" :rows="3" class="config-width" placeholder="OldName => NewName"></el-input>
					</el-form-item>
					<el-form-item label="制作组">
						<el-input v-model="mediaConfig.customReleaseGroups" type="textarea" :rows="3" class="config-width"></el-input>
					</el-form-item>
					<el-form-item label="自定义标签">
						<el-input v-model="mediaConfig.customization" type="textarea" :rows="3" class="config-width"></el-input>
					</el-form-item>
				</div>
				<el-button type="primary" :loading="saveMediaConfigLoading" @click="saveMediaConfig">保存刮削配置</el-button>
			</el-form>
		</div>
	</div>
</template>

<script>
	import {
		openlistGet,
		openlistPost,
		openlistPut,
		openlistDelete
	} from "@/api/job";
	import {
		getMediaScrapingConfig,
		saveMediaScrapingConfig
	} from "@/api/mediaScraping";
	export default {
		name: 'Engine',
		components: {},
		data() {
			return {
				openlistList: [],
				getLoading: false,
				deleteLoading: false,
				editLoading: false,
				configMode: 'openlist',
				mediaConfig: this.defaultMediaConfig(),
				extensionsText: '',
				saveMediaConfigLoading: false,
				editData: null,
				editFlag: false,
				editShow: false,
				editRule: {
					url: [{
						required: true,
						message: '请输入地址',
						trgger: 'blur'
					}]
				},
				addRule: {
					url: [{
						required: true,
						message: '请输入地址',
						trgger: 'blur'
					}],
					token: [{
						required: true,
						message: '请输入令牌，请到OpenList管理-设置-其他中复制，保存后不要重置令牌否则令牌失效',
						trgger: 'blur'
					}]
				}
			};
		},
		created() {
			if (this.$route.query && this.$route.query.type === 'mediaScraping') {
				this.configMode = 'mediaScraping';
			}
			this.getOpenlistList();
			this.getMediaConfig();
		},
		beforeDestroy() {},
		methods: {
			getOpenlistList() {
				this.getLoading = true;
				openlistGet().then(res => {
					this.getLoading = false;
					this.openlistList = res.data;
				}).catch(err => {
					this.getLoading = false;
				})
			},
			defaultMediaConfig() {
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
			getMediaConfig() {
				getMediaScrapingConfig().then(res => {
					this.mediaConfig = Object.assign(this.defaultMediaConfig(), res.data || {});
					this.extensionsText = (this.mediaConfig.mediaExtensions || []).join(',');
				})
			},
			buildMediaConfig() {
				const defaultOpenlistId = this.mediaConfig.defaultOpenlistId || null;
				return {
					...this.mediaConfig,
					defaultOpenlistId,
					openlistIds: defaultOpenlistId ? [defaultOpenlistId] : [],
					mediaExtensions: (this.extensionsText || '').split(',').map(item => item.trim()).filter(item => item)
				};
			},
			saveMediaConfig() {
				this.saveMediaConfigLoading = true;
				saveMediaScrapingConfig(this.buildMediaConfig()).then(res => {
					this.mediaConfig = Object.assign(this.defaultMediaConfig(), res.data || {});
					this.extensionsText = (this.mediaConfig.mediaExtensions || []).join(',');
					this.$message({
						message: res.msg,
						type: 'success'
					});
					this.saveMediaConfigLoading = false;
				}).catch(() => {
					this.saveMediaConfigLoading = false;
				})
			},
			addShow() {
				this.editFlag = false;
				this.editData = {
					remark: '',
					url: '',
					token: ''
				}
				this.editShow = true;
			},
			editShowDialog(row) {
				this.editData = {
					...row,
					token: ''
				};
				this.editFlag = true;
				this.editShow = true;
			},
			closeShow() {
				this.editShow = false;
			},
			submit() {
				this.$refs.addRule.validate((valid) => {
					if (valid) {
						this.editData.url = this.ensureHttpPrefix(this.editData.url);
						this.editLoading = true;
						if (this.editFlag) {
							openlistPut(this.editData).then(res => {
								this.editLoading = false;
								this.$message({
									message: res.msg,
									type: 'success'
								});
								this.closeShow();
								this.getOpenlistList();
							}).catch(err => {
								this.editLoading = false;
							})
						} else {
							openlistPost(this.editData).then(res => {
								this.editLoading = false;
								this.$message({
									message: res.msg,
									type: 'success'
								});
								this.closeShow();
								this.getOpenlistList();
							}).catch(err => {
								this.editLoading = false;
							})
						}
					}
				})
			},
			delOpenlist(openlistId) {
				this.$confirm("操作不可逆，将永久删除该引擎，请确认没有作业使用该引擎，否则会导致错误，仍要删除吗？", '提示', {
					confirmButtonText: '确定',
					cancelButtonText: '取消',
					type: 'warning'
				}).then(() => {
					this.deleteLoading = true;
					openlistDelete(openlistId).then(res => {
						this.deleteLoading = false;
						this.$message({
							message: res.msg,
							type: 'success'
						});
						this.getOpenlistList();
					}).catch(err => {
						this.deleteLoading = false;
					})
				});
			},
			ensureHttpPrefix(url) {
				if (!/^https?:\/\//i.test(url)) {
					if (url.startsWith('//')) {
						return 'http:' + url;
					}
					return 'http://' + url;
				}
				return url;
			}
		}
	}
</script>

<style lang="scss" scoped>
	.engine {
		box-sizing: border-box;
		width: 100%;
		height: 100%;

		.loading-box {
			box-sizing: border-box;
			width: 100%;
			height: 100%;
		}

		.engine-top {
			padding: 16px 16px 0;
		}

		.config-mode {
			width: 160px;
		}

		.card-box {
			box-sizing: border-box;
			padding: 8px;
			display: grid;
			grid-template-columns: repeat(auto-fill, minmax(340px, 2fr));
			width: 100%;

			.card-item {
				background-color: #292b3c;
				border-radius: 5px;
				border: 1px solid;
				border-color: transparent;
				height: 110px;
				margin: 8px;
				padding: 6px;

				.card-item-top {
					display: flex;
					align-items: center;
					justify-content: center;

					.card-item-user {
						font-size: 18px;
						display: flex;

						.card-item-remark {
							margin-left: 6px;
							color: #d6d12f;
							max-width: 120px;
							white-space: nowrap;
							overflow: hidden;
							text-overflow: ellipsis;
						}
					}

					.card-item-url {
						margin-top: 8px;
						font-size: 12px;
					}
				}

				.card-item-bottom {
					display: flex;
					align-items: center;
					justify-content: center;
					margin-top: 12px;
				}
			}

			.card-add {
				font-size: 32px;
				cursor: pointer;
				display: flex;
				justify-content: center;
				align-items: center;
			}

			.card-item:hover {
				border-color: #409eff;
				background-color: #3d415a;
			}

			.card-add:hover {
				font-size: 32px;
				color: #409eff;
				font-weight: bold;
			}
		}

		.scraping-config {
			padding: 16px;
			max-width: 880px;

			.config-block {
				background-color: #292b3c;
				border-radius: 5px;
				padding: 16px 16px 4px;
				margin-bottom: 14px;
			}

			.block-title {
				font-size: 16px;
				font-weight: bold;
				margin-bottom: 14px;
			}

			.config-width {
				width: 680px;
				max-width: 100%;
			}

			.short-width {
				width: 180px;
			}

			.option-url {
				float: right;
				color: #8492a6;
				font-size: 12px;
				margin-left: 18px;
			}

			.tip-text {
				margin: 0 14px 0 8px;
				color: #909bd4;
				font-size: 13px;
			}
		}

	}
</style>
