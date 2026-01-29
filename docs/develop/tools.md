# 开发工具

🚧施工中🚧

## 辅助工具

- [VSCode插件](#vscode-plugins)
- [代码格式化工具](#代码格式化工具)

## VSCode 插件 <a id="vscode-plugins"></a>

好的插件可以提高您的开发效率，事半功倍。

- [Maa Pipeline Support](https://marketplace.visualstudio.com/items?itemName=nekosu.maa-support) | MaaFramework 插件，提供调试、截图、获取ROI、取色等功能
- [markdownlint](https://marketplace.visualstudio.com/items?itemName=DavidAnson.vscode-markdownlint) | Markdown 语法检查插件

## 代码格式化工具

代码格式化可统一代码风格，提高代码可读性，降低代码维护成本。

目前启用的格式化工具如下：

| 文件类型 | 格式化工具 |
| --- | --- |
| JSON/Yaml | [prettier](https://prettier.io/) |
| Markdown | [MarkdownLint](https://github.com/DavidAnson/markdownlint-cli2) |

### 利用 Pre-commit Hooks 自动进行代码格式化

1. 确保你的电脑上有 Python 与 Node 环境

2. 在项目根目录下执行以下命令

    ```bash
    pip install pre-commit
    pre-commit install
    ```

如果pip安装后依然无法运行pre-commit，请确认pip安装地址已被添加到PATH

接下来，每次提交时都将会自动运行格式化工具，来确保你的代码格式符合规范

### 格式化配置

#### Oxipng

对应文件 `.pre-commit-config.yaml` 中以下部分：

```yaml
- repo: https://github.com/shssoichiro/oxipng
  rev: v9.1.2
  hooks:
    - id: oxipng
      args: ["-q", "-o", "2", "-s", "--ng"]
```

[参数说明](https://github.com/shssoichiro/oxipng)

#### MarkdownLint

对应文件 `.pre-commit-config.yaml` 中以下部分：

```yaml
- repo: https://github.com/DavidAnson/markdownlint-cli2
  rev: v0.13.0
  hooks:
    - id: markdownlint-cli2
      files: ^docs/.*|^README\.md$
      types:
        - markdown
      args: ["--fix", "--config", "docs/.markdownlint.yaml", "#**/node_modules"]
```

配置文件 `docs/.markdownlint.yaml` , [具体规则](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md)

#### Prettier

对应文件 `.pre-commit-config.yaml` 中以下部分：

```yaml
- repo: https://github.com/pre-commit/mirrors-prettier
  rev: v4.0.0-alpha.8
  hooks:
    - id: prettier
      types_or:
        - yaml
        - json
```

配置文件 `.prettierrc.yaml` , [具体规则](https://prettier.io/docs/en/options.html)

这里用到了 "prettier-plugin-multiline-arrays" 插件，目的是保持多行数组，不需要则可删去。
关联文件 `package.json` 以及 `package-lock.json` 。
