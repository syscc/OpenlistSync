# AGENTS.md

## 项目协作约定

- 测试阶段禁止将源码编译为二进制程序。
- 调试、验证、排查问题时，全程优先使用原始源代码直接运行。
- 不生成可执行二进制，不打包二进制文件，不走 PyInstaller。
- 前端本地验证优先使用 Vue dev server，不执行 `npm run build`，除非用户明确要求验证 Docker/Release 构建产物。
- 后端本地验证优先使用 Python 解释器直接运行 `main.py`。
- 不要随意删除或重置 `data/` 下的数据库、配置、密钥和日志；这些通常是用户本地运行状态。

## 本地源码运行

- 后端源码运行：

```bash
.venv/bin/python main.py
```

- 前端源码运行：

```bash
cd frontend
VUE_APP_BASE_API=/svr npm run dev -- --host 0.0.0.0 --port 8080
```

- 也可以使用源码启动脚本：

```bash
./data/start.py
./data/start.py -s
./data/start.py -r
```

## 验证习惯

- Python 修改后至少做语法检查，避免生成字节码缓存：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from pathlib import Path
for path in Path('.').rglob('*.py'):
    if any(part in {'.venv', 'frontend', '.git'} for part in path.parts):
        continue
    compile(path.read_text(encoding='utf-8'), str(path), 'exec')
print('python syntax ok')
PY
```

- 前端修改后使用 dev server 编译验证，不用 production build：

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 8091
```

- 验证完成后关闭临时 dev server，避免遗留额外端口。
- 确认常用源码服务：

```bash
curl -s -o /dev/null -w 'backend:%{http_code}\n' http://127.0.0.1:8023/
curl -s -o /dev/null -w 'frontend:%{http_code}\n' http://127.0.0.1:8080/
```

## 文档与版本

- 新增功能、菜单、接口、数据库表或目录结构变化时，同步更新 `README.md`。
- README 中的项目目录树需要跟随主要目录和新增核心文件更新。
- 涉及用户可见功能变更时，检查是否需要更新 `doc/changelog/` 和 `version.txt`。
- 发版或用户明确要求更新版本时，需要在 `version.txt` 中将版本号递增一个版本。
- 版本号递增按 `vX.Y.Z` 三段处理，每段数字最大为 9；例如 `v0.1.9` 的下一版是 `v0.2.0`，`v0.9.9` 的下一版是 `v1.0.0`。
- 发版或用户明确要求更新版本时，需要在 `doc/changelog/` 中新增对应版本更新日志。
- `version.txt` 和 `doc/changelog/vX.Y.Z.md` 的版本号需要保持一致。
- 未经用户明确要求，不主动改版本号；如果用户要求发版或准备发布，再同步更新版本文件和 changelog。

## 前后端注意事项

- 本地访问 `8080` 是前端源码 dev server，能实时看到源码 UI 改动。
- 本地访问 `8023` 是后端托管的静态前端，读取 `frontend/dist` 或 `front`，在未执行前端 build 时可能仍是旧 UI。
- Docker 默认只暴露 `8023`，发布镜像时需要通过构建流程生成并打入新的前端静态产物。
- 前端 API 默认走 `/svr`，dev server 通过 `frontend/vue.config.js` 代理到后端 `8023`。

## 数据库与配置

- SQLite 数据库位于 `data/openlistsync.db`。
- 全局排除项保存在 `system_config` 表，键名为 `global_exclude`。
- 数据库迁移在 `common/sqlInit.py` 中维护，增加表或字段时要提升 `cuVersion` 并写兼容迁移。
- 运行配置优先级为 `data/config.ini` > 环境变量 > 默认值。

## Git 与文件处理

- 不要回滚用户已有改动。
- 不要使用 `git reset --hard` 或 `git checkout --` 这类破坏性命令，除非用户明确要求。
- `.venv/`、`frontend/node_modules/`、`data/` 等运行环境或本地状态不应作为功能改动提交。
- 手动编辑文件优先使用 `apply_patch`。
