### 更新内容

[//]: # (#### 💡 新特性)

#### 🐛 修复

- 修复为全部用户执行米游社任务的 **`/任务 *`** 命令 (#390)
  - `TypeError: object NoneType can't be used in 'await' expression`
- 修复为全部用户执行米游社任务和游戏签到的 **`/任务 *`** **`/签到 *`** 命令**开始执行提示**被包含在合并转发的问题 (#366)

#### 🔧 杂项

- 偏好设置中 `global_geetest` 默认值改为 `False` (#373)

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

**Full Changelog**: https://github.com/Ljzd-PRO/nonebot-plugin-mystool/compare/v2.9.0…v2.10.0