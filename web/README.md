# OpenListSync Web

当前前端基于 Vue 3、Vite、Element Plus 与 Pinia。开发环境 API 默认代理到
`http://127.0.0.1:8023`。

## 源码运行

```sh
npm install
npm run dev -- --host 0.0.0.0 --port 8080
```

## 源码验证

```sh
npm test
npm run lint
```

`npm run lint` 只检查，不会自动修改文件；需要主动修复格式时使用
`npm run lint:fix`。生产构建由发布流程处理，本地功能调试按项目根目录
`AGENTS.md` 使用 Vite dev server。
