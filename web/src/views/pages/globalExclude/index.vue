<template>
	<div class="global-exclude-page">
		<div class="global-exclude">
			<div class="box-heading">
					<div class="box-icon"><ShieldBan :size="20" aria-hidden="true" /></div>
				<div>
					<div class="box-title">{{ $t('globalExclude.title') }}</div>
					<div class="box-subtitle">{{ $t('globalExclude.syntax') }}</div>
				</div>
			</div>
			<div class="syntax">
				<button type="button" @click="toIgnore" class="to-link"><BookOpen :size="15" />{{ $t('globalExclude.tutorial') }}<ExternalLink :size="14" /></button>
			</div>
			<div class="label-list-box">
					<el-input v-model="globalExcludeTmp" :placeholder="$t('globalExclude.placeholder')" @keyup.enter="addGlobalExclude">
						<template #append>
							<el-button @click="addGlobalExclude"><Plus :size="15" />{{ $t('common.add') }}</el-button>
						</template>
					</el-input>
				<div v-for="(item, index) in systemConfig.globalExclude" :key="item + index" class="label-list-item">
					<div class="bg-3 label-list-item-left">{{item}}</div>
						<el-button type="danger" text size="small" @click="delGlobalExclude(index)"><Trash2 :size="15" />{{ $t('common.delete') }}</el-button>
					</div>
					<div v-if="systemConfig.globalExclude.length === 0" class="empty-rule">{{ $t('globalExclude.empty') }}</div>
				</div>
			<el-button type="primary" :loading="configLoading" @click="saveConfig"><Save :size="15" />{{ $t('globalExclude.save') }}</el-button>
		</div>
	</div>
</template>

<script>
	import { BookOpen, ExternalLink, Plus, Save, ShieldBan, Trash2 } from '@lucide/vue';
	import {
		getSystemConfig,
		saveSystemConfig
	} from "@/api/system";

	export default {
		name: 'GlobalExclude',
		components: { BookOpen, ExternalLink, Plus, Save, ShieldBan, Trash2 },
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
		padding: 0 0 24px;
		width: 100%;
		box-sizing: border-box;

		.global-exclude {
			padding: 24px;
			background-color: var(--home-item-background-color);
			border: 1px solid var(--border-color);
			width: min(720px, 100%);
			box-sizing: border-box;
			border-radius: var(--radius-md);
			box-shadow: var(--shadow-xs);

			.box-heading {
				display: flex;
				align-items: flex-start;
				gap: 12px;
				margin-bottom: 12px;
			}

			.box-icon {
				width: 40px;
				height: 40px;
				flex: 0 0 auto;
				display: grid;
				place-items: center;
				color: var(--warning-color);
				border-radius: var(--radius-md);
				background: var(--warning-soft);
			}

			.box-title {
				font-size: 18px;
				font-weight: 750;
				letter-spacing: 0;
			}

			.box-subtitle {
				margin-top: 3px;
				color: var(--text-muted);
				font-size: 13px;
			}

			.syntax {
				margin: 0 0 18px 52px;
				color: var(--text-secondary);
				line-height: 1.5;
			}

			.to-link {
				display: inline-flex;
				align-items: center;
				gap: 6px;
				padding: 0;
				border: 0;
				color: var(--active-color);
				background: transparent;
				cursor: pointer;
			}

			.to-link:hover {
				text-decoration: underline;
			}

			.label-list-box {
				width: 100%;
				margin-bottom: 16px;
			}

			.label-list-item {
				display: flex;
				align-items: center;
				margin-top: 8px;
				padding: 7px 8px 7px 12px;
				border: 1px solid var(--border-color);
				border-radius: var(--radius-sm);
				background: var(--surface-inset);
			}

			.label-list-item-left {
				flex: 1;
				min-width: 0;
				margin-right: 8px;
				padding: 0;
				height: auto;
				line-height: 1.5;
				color: var(--warning-color);
				border: 0;
				background: transparent;
				font-family: var(--font-mono);
				font-size: 13px;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
			}

			.empty-rule {
				margin-top: 10px;
				padding: 24px 16px;
				border: 1px dashed var(--border-strong);
				border-radius: var(--radius-sm);
				color: var(--text-muted);
				font-size: 14px;
				text-align: center;
			}
		}
	}

	@media (max-width: 768px) {
		.global-exclude-page {
			padding: 0 0 16px;
			font-size: 14px;

			.global-exclude {
				padding: 18px 14px;
			}

			.global-exclude .syntax {
				margin-left: 0;
			}

			.label-list-item-left {
				margin-right: 8px;
			}
		}
	}
</style>
