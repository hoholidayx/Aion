# Aion 本地工作区

```text
Aion/
├── AionUi/    Web 界面、独立 Web CLI 和桌面端源码
├── AionCore/  Rust 后端，提供 API、认证和会话管理
├── aionrs/    Rust Agent 引擎，提供模型接入、工具和记忆
├── aion-openai-image-mcp/  独立的供应商生图适配服务
├── build-tools/  本机可复用的构建工具和缓存
├── local/     本机配置和私有脚本
├── notes/     本地说明、排查记录和维护笔记
└── tmp/       可清理的日志、临时文件和打包中间产物
```

## 仓库与构建

- 子项目各自是独立的 Git 仓库。修改前读取对应仓库的 `AGENTS.md`，按各仓库的规则验证并分别提交。
- 此工作区默认在各仓库的本地 `main` 提交。用户要求推送时，先核对 `origin` 指向用户自己的仓库，再直接推送到 `origin/main`。AionUi、AionCore 和 aionrs 使用 `just push origin main`。仅在用户明确要求时创建功能分支、使用其他目标分支或走 PR。
- 保持三个仓库同级并保留目录名。AionCore 的 Cargo 依赖通过 `../aionrs` 读取本地源码，跨仓库构建时依次检查 aionrs、AionCore 和 AionUi。
- 在 `AionUi/` 默认用 `bun run build` 或 `just build`，只构建独立 Web，产物位于 `out/web-renderer/`。仅构建 Web 时用 `bun install --frozen-lockfile --ignore-scripts` 安装依赖。Electron 预检、原生模块重建和桌面打包走 `build-mac` 等显式桌面命令。
- Web 构建会生成 Brotli 和 gzip 资源并检查首屏体积预算。构建通过后，再用 `node scripts/pack-web-cli.js` 将 Web 产物和 AionCore 打成独立发布包。
- 生图适配服务是独立仓库，用 `uv sync --locked` 安装依赖，`uv run --locked aion-image-mcp-service` 管理服务，`uv run --locked pytest` 验证。保持与 Aion Web 独立启停，供应商配置、凭据和任务数据存放在源码目录之外。
- 本机正式部署范围为 Web 和 AionCore。构建与打包流程见 [AionUi 开发文档](AionUi/docs/contributing/development.md)。本地配置、凭据和临时产物放在工作区的本地目录中，避免进入源码仓库。

## 实现与复核

- 写方案和改代码前，沿正常入口读到实际执行层。先查找并复用现有模块、方法、接口、类型、常量和文案。确实需要新增时，在方案或复核中说明现有实现欠缺的语义，以及新代码应归属的层。
- 将校验、查询和锁放在需要它们的操作及对象范围内。优先复用调用链已加载的数据和现有生命周期控制。新增持久状态或并发机制前，分别说明它要处理的失败、重试、重启或竞态，并保持其他调用者的默认行为和错误语义。
- 提交前按实际 diff 自查新增定义是否重复、实现是否跨层、通用路径是否增加了无关查询或锁。涉及不可逆操作时，验证部分失败、重复请求和并发下的结果，并覆盖已有调用者依赖的行为。

## 本机构建工具

- 构建前优先复用 `build-tools/` 中已有的 Rust 1.96.1（含 rustfmt、Clippy）、Bun 1.4.4（`bun`、`bunx`）和缓存。清理 `tmp/` 时保留 `build-tools/`。
- 在 `Aion/` 根目录运行以下命令，为当前终端配置本机工具。Node.js 和 cargo-nextest 沿用系统 PATH。

  ```sh
  export AION_BUILD_TOOLS="$PWD/build-tools"
  export CARGO_HOME="$AION_BUILD_TOOLS/cargo"
  export RUSTUP_HOME="$AION_BUILD_TOOLS/rustup"
  export PATH="$AION_BUILD_TOOLS/tool-bin:$CARGO_HOME/bin:$PATH"
  ```

- Cargo 测试和正式构建分别通过 `CARGO_TARGET_DIR` 使用 `$AION_BUILD_TOOLS/test-target` 和 `$AION_BUILD_TOOLS/release-target`。正式构建使用 `cargo +1.96.1`，保留开发文档里的 release strip 设置。使用此目录构建的后端在 `$AION_BUILD_TOOLS/release-target/release/aioncore`，打包时以此为准。npm 下载缓存位于 `$AION_BUILD_TOOLS/npm-cache`。
- Cargo 会按源码、路径和构建选项重新判断缓存。路径移动后首次构建可能重新编译部分依赖，后续保持工具和缓存路径稳定。

## 本机服务管理

- 从 `Aion/` 运行 `./manage-services.py` 打开交互入口，也可以显式传入 `--interactive`。使用 `./manage-services.py {start|stop|restart|status} [all|web|image-mcp]` 直接执行命令。省略服务时操作全部，任一目标失败或状态不健康时返回非零。
- `web` 包含 Web CLI 及其 AionCore 子进程，`image-mcp` 管理本机生图服务。统一入口复用各自的后台管理器和现有配置。批量启动时先启动生图服务，批量停止时先停止 Web。移动仓库或替换发布包前先停止受影响的服务，完成后检查进程、监听端口和 HTTP 健康状态。
- 发布包位于 `AionUi/out/web-production/`，默认监听 `0.0.0.0:25808`。需要本机监听时，在启动或重启命令前设置 `AIONUI_ALLOW_REMOTE=0`。
- Web 用户数据和服务日志位于 `~/.aionui-web/`，macOS 的 AionRS 全局配置和记忆位于 `~/.aionrs/`。清理 `tmp/` 时保留这些目录以及正式发布包和部署备份。
- 生图服务默认监听 `127.0.0.1:8790`，本机配置和日志位于 `~/.aion-openai-image-mcp/`。
