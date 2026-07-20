# GitHub 推送指南

## 当前状态

代码已成功提交到本地仓库，但推送到 GitHub 需要认证。

---

## 推送方法

### 方法 1: 使用 SSH（推荐）

#### 1. 生成 SSH 密钥（如果没有）
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

#### 2. 添加 SSH 密钥到 GitHub
```bash
# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 复制公钥，然后在 GitHub 网页：
# Settings → SSH and GPG keys → New SSH key
```

#### 3. 更改远程仓库为 SSH
```bash
git remote set-url origin git@github.com:realplayerc4/nav24r.git
```

#### 4. 推送
```bash
git push origin main
```

---

### 方法 2: 使用 Personal Access Token

#### 1. 创建 GitHub Token
- 访问 GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- 点击 "Generate new token"
- 勾选 `repo` 权限
- 生成并保存 token

#### 2. 使用 Token 推送
```bash
# 格式：https://<token>@github.com/username/repo.git
git remote set-url origin https://<YOUR_TOKEN>@github.com/realplayerc4/nav24r.git

# 推送
git push origin main
```

---

### 方法 3: 使用 GitHub CLI（推荐）

#### 1. 安装 GitHub CLI
```bash
# Ubuntu/Debian
sudo apt install gh

# 或
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

#### 2. 登录 GitHub
```bash
gh auth login
```

#### 3. 推送
```bash
git push origin main
```

---

### 方法 4: 临时使用 HTTPS + Token

```bash
# 推送时输入用户名和密码（token）
git push https://github.com/realplayerc4/nav24r.git main

# Username: 你的 GitHub 用户名
# Password: 你的 Personal Access Token（不是密码）
```

---

## 当前推送状态

```
✅ 本地提交：成功（d5fd6e4）
✅ 提交内容：27 个文件，+4736 行代码
⏳ 远程推送：需要认证

待推送内容：
- ROS2 Jazzy 测试报告
- 控制面板增强功能
- 配置文件系统
- 完整文档
- 工具脚本
```

---

## 推荐方案

**最简单**: 使用 GitHub CLI
```bash
sudo apt install gh
gh auth login
git push origin main
```

**最安全**: 使用 SSH
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# 添加公钥到 GitHub
git remote set-url origin git@github.com:realplayerc4/nav24r.git
git push origin main
```

---

## 验证推送成功

推送成功后，可以验证：

```bash
# 查看远程仓库状态
git remote show origin

# 查看提交历史
git log --oneline -5

# 在浏览器打开
# https://github.com/realplayerc4/nav24r/commits/main
```

---

## 需要帮助？

如果遇到问题，可以：
1. 检查网络连接
2. 确认 GitHub 账户权限
3. 使用 `git push -v origin main` 查看详细信息
4. 查看 GitHub 文档：https://docs.github.com/en/authentication