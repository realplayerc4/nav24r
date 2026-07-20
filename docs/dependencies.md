# PyYAML 包添加到项目依赖

## 问题

控制面板现在使用 PyYAML 来加载配置文件，需要确保系统中安装了此包。

## 解决方案

PyYAML 已在系统中安装（验证通过）。

## 安装方法（如需要）

```bash
# Ubuntu/Debian
sudo apt install python3-yaml

# 或使用 pip
pip3 install pyyaml
```

## 验证

```bash
python3 -c "import yaml; print('PyYAML 已安装')"
```

## 注意事项

- PyYAML 是 Python 标准库的一部分（在某些系统中）
- 在 Ubuntu 24.04 中通常已预装
- 如果没有安装，控制面板会使用默认配置