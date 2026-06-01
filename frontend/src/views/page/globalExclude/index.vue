<template>
	<div class="global-exclude-page">
		<div class="global-exclude">
			<div class="box-title">全局排除项规则</div>
			<div class="syntax">
				<div>类gitignore，根目录为每个同步作业的来源或目标目录</div>
				<span @click="toIgnore" class="to-link">点击查看排除项简易教程</span>
			</div>
			<div class="label-list-box">
				<el-input v-model="globalExcludeTmp" placeholder="输入后点添加才生效" @keyup.enter.native="addGlobalExclude">
					<el-button slot="append" @click="addGlobalExclude">添加</el-button>
				</el-input>
				<div v-for="(item, index) in systemConfig.globalExclude" :key="item + index" class="label-list-item">
					<div class="bg-3 label-list-item-left">{{item}}</div>
					<el-button type="danger" size="mini" @click="delGlobalExclude(index)">删除</el-button>
				</div>
				<div v-if="systemConfig.globalExclude.length === 0" class="empty-rule">暂无全局排除项</div>
			</div>
			<el-button type="primary" :loading="configLoading" @click="saveConfig">保存全局规则</el-button>
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
				}).catch(err => {
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
			background-color: #292b3c;
			width: 560px;
			box-sizing: border-box;
			border-radius: 3px;

			.box-title {
				margin-bottom: 14px;
				font-size: 18px;
				font-weight: bold;
			}

			.syntax {
				margin-bottom: 16px;
				color: #909bd4;
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
				color: #909bd4;
				font-size: 14px;
			}
		}
	}
</style>
