<template>
	<div class="global-exclude-page">
		<div class="global-exclude">
			<div class="box-title">{{ $t('globalExclude.title') }}</div>
			<div class="syntax">
				<div>{{ $t('globalExclude.syntax') }}</div>
				<span @click="toIgnore" class="to-link">{{ $t('globalExclude.tutorial') }}</span>
			</div>
			<div class="label-list-box">
					<el-input v-model="globalExcludeTmp" :placeholder="$t('globalExclude.placeholder')" @keyup.enter="addGlobalExclude">
						<template #append>
							<el-button @click="addGlobalExclude">{{ $t('common.add') }}</el-button>
						</template>
					</el-input>
				<div v-for="(item, index) in systemConfig.globalExclude" :key="item + index" class="label-list-item">
					<div class="bg-3 label-list-item-left">{{item}}</div>
						<el-button type="danger" size="small" @click="delGlobalExclude(index)">{{ $t('common.delete') }}</el-button>
					</div>
					<div v-if="systemConfig.globalExclude.length === 0" class="empty-rule">{{ $t('globalExclude.empty') }}</div>
				</div>
			<el-button type="primary" :loading="configLoading" @click="saveConfig">{{ $t('globalExclude.save') }}</el-button>
		</div>
	</div>
</template>

<script>
	import {
		getSystemConfig,
		saveSystemConfig
	} from "@/api/system";

	export default {
		name: 'GlobalExclude',
		data() {
			return {
				systemConfig: {
					globalExclude: []
				},
				globalExcludeTmp: '',
				configLoading: false
			};
		},
		created() {
			this.getConfig();
		},
		methods: {
			getConfig() {
				getSystemConfig().then(res => {
					const globalExclude = res.data && res.data.globalExclude ? res.data.globalExclude : '';
					this.systemConfig.globalExclude = globalExclude ? globalExclude.split(':') : [];
				})
			},
			addGlobalExclude() {
				const value = (this.globalExcludeTmp || '').trim();
				if (value !== '') {
					this.systemConfig.globalExclude.push(value);
				}
				this.globalExcludeTmp = '';
			},
			delGlobalExclude(index) {
				this.systemConfig.globalExclude.splice(index, 1);
			},
			saveConfig() {
				this.configLoading = true;
				saveSystemConfig({
					globalExclude: this.systemConfig.globalExclude.join(':')
				}).then(res => {
					const globalExclude = res.data && res.data.globalExclude ? res.data.globalExclude : '';
					this.systemConfig.globalExclude = globalExclude ? globalExclude.split(':') : [];
					this.$message({
						message: res.msg,
						type: 'success'
					});
					this.configLoading = false;
					}).catch(() => {
					this.configLoading = false;
				})
			},
			toIgnore() {
				window.open('https://github.com/syscc/OpenlistSync?tab=readme-ov-file#%E6%8E%92%E9%99%A4%E9%A1%B9%E8%A7%84%E5%88%99%E7%AE%80%E5%8D%95%E8%AF%B4%E6%98%8E');
			}
		}
	}
</script>

<style lang="scss" scoped>
	.global-exclude-page {
		padding: 32px;
		font-size: 16px;
		width: 100%;
		box-sizing: border-box;

		.global-exclude {
			padding: 24px 16px;
			background-color: var(--home-item-background-color);
			border: 1px solid var(--border-color);
			width: min(560px, 100%);
			box-sizing: border-box;
			border-radius: 6px;

			.box-title {
				margin-bottom: 14px;
				font-size: 18px;
				font-weight: bold;
			}

			.syntax {
				margin-bottom: 16px;
				color: var(--text-secondary);
				line-height: 24px;
			}

			.to-link {
				color: #409eff;
				cursor: pointer;
			}

			.to-link:hover {
				color: #66b1ff;
			}

			.label-list-box {
				width: 100%;
				margin-bottom: 16px;
			}

			.label-list-item {
				display: flex;
				align-items: center;
				margin-top: 10px;
			}

			.label-list-item-left {
				flex: 1;
				min-width: 0;
				margin-right: 12px;
				padding: 0 12px;
				height: 32px;
				line-height: 32px;
				border-radius: 3px;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
			}

			.empty-rule {
				margin-top: 12px;
				color: var(--text-muted);
				font-size: 14px;
			}
		}
	}

	@media (max-width: 768px) {
		.global-exclude-page {
			padding: 12px 10px 20px;
			font-size: 14px;

			.global-exclude {
				padding: 16px 12px;
			}

			.label-list-item-left {
				margin-right: 8px;
			}
		}
	}
</style>
