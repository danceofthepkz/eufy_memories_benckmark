# GitHub Actions Workflows

## PlantUML 自动渲染

`render-plantuml.yml` 工作流会自动将项目中的 PlantUML 文件（`.puml`）渲染为 PNG 图片。

### 触发条件

- 当 `.puml` 文件被推送或修改时
- 当工作流文件本身被修改时
- 手动触发（在 GitHub Actions 页面）

### 工作流程

1. **检出代码**: 获取最新的代码
2. **设置 Java**: 安装 Java 17（PlantUML 需要）
3. **下载 PlantUML**: 下载最新版本的 PlantUML JAR 文件
4. **渲染图片**: 查找所有 `.puml` 文件并渲染为 PNG
5. **提交图片**: 自动将生成的 PNG 文件提交到仓库
6. **上传制品**: 将 PNG 文件作为 artifacts 上传（保留 30 天）

### 使用方法

#### 自动触发

只需推送包含 `.puml` 文件的更改：

```bash
git add *.puml
git commit -m "Update PlantUML diagrams"
git push
```

工作流会自动运行并生成 PNG 文件。

#### 手动触发

1. 进入 GitHub 仓库页面
2. 点击 "Actions" 标签
3. 选择 "Render PlantUML Diagrams" 工作流
4. 点击 "Run workflow" 按钮

### 生成的文件

生成的 PNG 文件会保存在与 `.puml` 文件相同的目录中，文件名相同但扩展名为 `.png`。

例如：
- `系统完整流程UML图.puml` → `系统完整流程UML图.png`
- `workflow/系统流程序列图.puml` → `workflow/系统流程序列图.png`

### 注意事项

1. **文件位置**: PNG 文件会与对应的 `.puml` 文件保存在同一目录
2. **自动提交**: 生成的 PNG 文件会自动提交到仓库（使用 `[skip ci]` 标记，避免循环触发）
3. **权限要求**: 工作流需要写入权限来提交文件，确保使用 `GITHUB_TOKEN` 或配置了适当的权限

### 故障排除

如果工作流失败：

1. 检查 PlantUML 语法是否正确
2. 查看工作流日志了解详细错误信息
3. 确保 `.puml` 文件路径正确
4. 检查是否有足够的权限提交文件

### 本地渲染（可选）

如果你想在本地渲染 PlantUML 文件：

```bash
# 安装 PlantUML
# macOS
brew install plantuml

# 或使用 Docker
docker run --rm -v "$PWD:/work" plantuml/plantuml:latest -tpng /work/*.puml

# 或使用 Java
java -jar plantuml.jar -tpng *.puml
```

### 相关链接

- [PlantUML 官方文档](https://plantuml.com/)
- [GitHub Actions 文档](https://docs.github.com/en/actions)

