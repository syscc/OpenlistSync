<template>
	<div class="pathSelect">
		<el-dialog top="8vh" :close-on-click-modal="false" :visible.sync="dialogShow" title="选择目录" width="520px"
			:before-close="closeShow" :append-to-body="true">
			<el-tree :props="props" :load="loadNode" lazy :highlight-current="true" :check-on-click-node="true"
				@node-click="nodeClick" v-if="dialogShow">
			</el-tree>
			<span slot="footer" class="dialog-footer">
				<el-button @click="closeShow">取 消</el-button>
				<el-button type="success" plain @click="mkdir" :disabled="cuPath == null">新建文件夹</el-button>
				<el-button type="primary" @click="submit" :loading="submitLoading"
					:disabled="cuPath == null">{{cuPath == null ? '请先选择路径' : '确 定'}}</el-button>
			</span>
		</el-dialog>
	</div>
</template>

<script>
	import {
		openlistGetPath,
		openlistMkdir
	} from "@/api/job";
	export default {
		name: 'PathSelect',
		components: {},
		props: {
			openlistId: {
				type: Number,
				default: null
			}
		},
		data() {
			return {
				dialogShow: false,
				pathLoading: false,
				submitLoading: false,
				cuPath: null,
				cuNode: null,
				props: {
					label: 'path',
					children: 'child',
					isLeaf: 'leaf'
				}
			};
		},
		created() {},
		beforeDestroy() {},
		methods: {
			show() {
				this.dialogShow = true;
			},
			async getPath(path) {
				this.pathLoading = true;
				try {
					let res = await openlistGetPath(this.openlistId, path);
					this.pathLoading = false;
					return res.data;
				} catch (err) {
					this.pathLoading = false;
					return [];
				}
			},
			async loadNode(node, resolve) {
				let path = '/';
				let cup = node;
				for (let i = 0; i < node.level; i++) {
					path = '/' + cup.data.path + path;
					cup = cup.parent;
				}
				return resolve(await this.getPath(path));
			},
			closeShow() {
				this.dialogShow = false;
				this.cuPath = null;
				this.cuNode = null;
			},
			nodeClick(dt, node, se) {
				let path = '/';
				let cup = node;
				for (let i = 0; i < node.level; i++) {
					path = '/' + cup.data.path + path;
					cup = cup.parent;
				}
				this.cuPath = path;
				this.cuNode = node;
			},
			mkdir() {
				this.$prompt('请输入文件夹名称', '新建文件夹', {
					confirmButtonText: '确定',
					cancelButtonText: '取消',
					inputPattern: /^[^/\\:*?"<>|]+$/,
					inputErrorMessage: '文件夹名称格式不正确'
				}).then(async ({
					value
				}) => {
					this.submitLoading = true;
					try {
						await openlistMkdir({
							openlistId: this.openlistId,
							path: this.cuPath + value
						});
						this.$message.success('创建成功');
						if (this.cuNode) {
							this.cuNode.loaded = false;
							this.cuNode.expand();
						}
					} catch (e) {
						console.error(e)
					}
					this.submitLoading = false;
				}).catch(() => {});
			},
			submit() {
				this.$emit('submit', this.cuPath);
				this.closeShow();
			}
		}
	}
</script>

<style lang="scss" scoped>
	.pathSelect {}
</style>