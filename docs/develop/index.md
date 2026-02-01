# 快速上手

> [!WARNING]
> 本项目目前的开发文档尚未完善！
>
> 你可以先阅读[M9A 开发须知](https://1999.fan/zh_cn/develop/development.html)以了解如何在本地以开发模式运行项目（本项目与M9A的项目结构类似，可以作为学习参考）。更多内容请自行学习MaaFramework的[开发文档](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/1.1-%E5%BF%AB%E9%80%9F%E5%BC%80%E5%A7%8B.md)的内容。

## 1. 开发环境配置

### 1.1 编辑器推荐

我们**强烈推荐**使用 [VSCode](https://code.visualstudio.com/Download) 进行开发，因为社区提供了优秀的 [Maa Pipeline Support](https://marketplace.visualstudio.com/items?itemName=nekosu.maa-support) VSCode 插件来进行调试。

### 1.2 必要软件安装

1. **安装 VSCode** - 代码编辑器
2. **安装 Git** - 版本控制工具
3. **安装 Python** - 开发语言（**≥3.12**，推荐使用 **Python 3.12.9** 版本）

### 1.3 可选开发工具

| 工具 | 简介 |
| --- | --- |
| [MaaDebugger](https://github.com/MaaXYZ/MaaDebugger) | 独立调试工具 |
| [Maa Pipeline Support](https://marketplace.visualstudio.com/items?itemName=nekosu.maa-support) | VSCode 插件，提供调试、截图、获取 ROI 、取色等功能 |
| [MFAToolsPlus](https://github.com/SweetSmellFox/MFAToolsPlus) | 独立截图、获取 ROI 及取色工具 |
| [MaaPipelineEditor](https://github.com/kqcoxn/MaaPipelineEditor) | 任务流程pipeline可视化工具 |

---

## 2. Python 安装详情

### 2.1 下载 Python

访问华为云镜像站下载 Python：

> [!NOTE]
> **镜像地址：** [https://repo.huaweicloud.com/python/3.12.9/](https://repo.huaweicloud.com/python/3.12.9/)
> **推荐下载：** [https://repo.huaweicloud.com/python/3.12.9/python-3.12.9.exe](https://repo.huaweicloud.com/python/3.12.9/python-3.12.9.exe)

### 2.2 安装 Python

运行下载的 Python 安装程序，**强烈建议**勾选 "Add Python to PATH" 选项，然后按照默认设置完成安装。

---

## 3. 克隆项目代码

使用 Git 克隆项目代码到本地：

```bash title="克隆项目代码"
git clone https://github.com/duorua/narutomobile.git
cd narutomobile
```

> [!TIP]
> 确保您已经安装了 Git 工具，否则无法执行上述命令。

---

## 4. 更新 Git 子模块

克隆完成项目代码后，在项目根目录下执行以下命令：

```bash title="更新Git子模块"
git submodule update --init --recursive
```

---

## 5. 安装 MaaFramework 依赖

MaaFramework 依赖可以通过以下两种方式之一安装：

### 5.1 方式一：直接下载发布包

1. 访问 [MaaFramework 发布页面](https://github.com/MaaXYZ/MaaFramework/releases)
2. 下载最新版本的发布包
3. 将下载的文件解压到项目根目录下的 `deps` 文件夹中

### 5.2 方式二：使用下载脚本 (推荐)

在项目根目录下执行以下命令：

```bash title="下载MaaFramework依赖"
python tools\download_maafw.py
```

## 6. 安装 Python 依赖

使用 pip 安装项目所需的 Python 依赖：

```bash title="安装Python依赖"
# 创建虚拟环境（可选但推荐）
python -m venv .venv
.venv\Scripts\activate  # Windows 系统
# source .venv/bin/activate  # Linux/macOS 系统

# 安装依赖
pip install -r requirements.txt
# 如果已经安装过依赖，使用以下命令更新
# pip install -U requirements.txt  # 或使用 pip install --upgrade requirements.txt
```

> [!NOTE]  
>
> - 虚拟环境可以隔离项目依赖，避免与全局环境冲突

---

## 7. 配置 OCR 模型

在项目的根目录运行以下命令配置 OCR 模型：

```bash title="配置OCR模型"
python ./tools/ci/configure.py
```

---

## 8. 验证安装

安装完成后，可以运行项目来验证是否安装成功：

```bash title="验证安装"
python -m agent.main <identifier>
```

`identifier`的值在`assets/interface.json`里

**✓ 如果能够正常启动，说明开发环境已经搭建完成！**

---

## 9. 开始开发

### 9.1 入门指南

1. 阅读 [M9A 开发须知](https://1999.fan/zh_cn/develop/development.html)，了解如何在本地以开发模式运行本项目（本项目与M9A的项目结构类似，可以作为学习参考）。

2. 如果不会写代码，但对某些功能的实现有明确的思路：
   - 参考 [任务流水线（Pipeline）协议](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/3.1-%E4%BB%BB%E5%8A%A1%E6%B5%81%E6%B0%B4%E7%BA%BF%E5%8D%8F%E8%AE%AE.md) 学习如何将思路转化为具体实现
   - 了解如何在 `assets\resource\base\pipeline` 中编写流水线文件
   - 学习 [Project Interface 协议](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/3.2-ProjectInterface%E5%8D%8F%E8%AE%AE.md#project-interface-%E5%8D%8F%E8%AE%AE)，了解如何让软件能够调用你写的流水线文件

3. 如果你有一定的 Python 基础，想要尝试为项目编写代码：
   - 阅读 [MaaFramework 集成接口](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/2.2-%E9%9B%86%E6%88%90%E6%8E%A5%E5%8F%A3%E4%B8%80%E8%A7%88.md) 并**结合本项目源码**以了解如何为项目开发高级功能
   - **重要提示**：纸上学来终觉浅，绝知此事要躬行。不结合代码实践读文档，等于白读。

4. 为项目贡献你所编写的内容，请参考 [牛牛也能看懂的 GitHub Pull Request 使用指南](https://maa.plus/docs/zh-cn/develop/pr-tutorial.html)

---

## 10. 常见问题与解决方案

### 10.1 运行项目问题

1. **错误**：提示 "Failed to load det or rec", "ocrer is null"
   **解决方案**：确保 MaaFramework 依赖已正确安装，且 OCR 模型文件完整

2. **错误**：提示找不到模块
   **解决方案**：检查是否已正确激活虚拟环境（如果使用了虚拟环境），或重新安装依赖

### 10.2 开发相关问题

1. **问题**：我在这个仓库里提了 Issue 很久没人回复
   **解决方案**：本项目目前紧缺人手，你可以先阅读文档自行尝试寻找解决方案。欢迎提交 PR 贡献代码！

---

## 完成

您已经成功搭建了 Maa Auto Naruto 的开发环境！

如果您在使用过程中遇到其他问题，请参考：

- [MaaFramework 官方文档](https://maafw.xyz/)

祝您开发愉快！
