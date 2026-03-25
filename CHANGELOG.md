### 更新内容

[//]: # (#### 💡 新特性)

#### 🐛 修复

- 修正讨论区签到、人机验证创建失败问题 (#421) by @Sakamakiiizayoi

[//]: # (#### 🔧 杂项)

### 更新方式

如果使用的是镜像源，可能需要等待镜像源同步才能更新至最新版

- 使用 nb-cli 命令：
  ```
  nb plugin update nonebot-plugin-mystool
  ```

- 或 pip 命令（如果使用了虚拟环境，需要先进入虚拟环境）：
  ```
  pip install --upgrade nonebot-plugin-mystool
  ```

### 兼容性

- V2 (`>=v2.0.0`) 的相关文件为 _`configV2.json`, `dataV2.json`, `.env`_，如果存在 V1 版本的文件，**会自动备份和升级**
- V1 (`>=v1.0.0, <v2.0.0`) 插件配置/数据文件为 _`plugin_data.json`_
- `<v1.0.0` 插件配置文件为 _`pluginConfig.json`_

**Full Changelog**: https://github.com/Ljzd-PRO/nonebot-plugin-mystool/compare/v2.10.1…v2.10.2