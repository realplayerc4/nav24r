#!/bin/bash
# GitHub 推送助手脚本

echo "========================================="
echo "GitHub 推送助手"
echo "========================================="
echo ""

# 检查是否有待推送的提交
COMMITS_AHEAD=$(git rev-list --count origin/main..main 2>/dev/null || echo "0")

if [ "$COMMITS_AHEAD" = "0" ]; then
    echo "✅ 本地仓库与远程同步，无需推送"
    exit 0
fi

echo "📊 待推送提交数: $COMMITS_AHEAD"
echo ""
echo "最近提交:"
git log --oneline -3
echo ""

# 检查是否已认证
if command -v gh &> /dev/null; then
    echo "检查 GitHub CLI 认证状态..."
    if gh auth status &> /dev/null; then
        echo "✅ 已通过 GitHub CLI 认证"
        echo ""
        echo "正在推送..."
        git push origin main
        echo ""
        echo "✅ 推送成功！"
        exit 0
    else
        echo "⚠️  GitHub CLI 未认证"
        echo ""
        echo "请运行以下命令进行认证："
        echo "  gh auth login"
        exit 1
    fi
fi

# 检查 SSH 密钥
if [ -f ~/.ssh/id_ed25519.pub ] || [ -f ~/.ssh/id_rsa.pub ]; then
    echo "检测到 SSH 密钥"
    echo ""
    echo "如果已添加到 GitHub，可以使用 SSH 推送："
    echo ""
    echo "  git remote set-url origin git@github.com:realplayerc4/nav24r.git"
    echo "  git push origin main"
    exit 1
fi

# 没有可用的认证方式
echo "❌ 未检测到可用的认证方式"
echo ""
echo "请选择以下方法之一："
echo ""
echo "方法 1: 使用 GitHub CLI（推荐）"
echo "  sudo apt install gh"
echo "  gh auth login"
echo "  git push origin main"
echo ""
echo "方法 2: 使用 Personal Access Token"
echo "  1. 访问 https://github.com/settings/tokens"
echo "  2. 创建 token（勾选 repo 权限）"
echo "  3. git push https://YOUR_TOKEN@github.com/realplayerc4/nav24r.git main"
echo ""
echo "方法 3: 使用 SSH 密钥"
echo "  ssh-keygen -t ed25519 -C \"your_email@example.com\""
echo "  cat ~/.ssh/id_ed25519.pub  # 复制公钥到 GitHub"
echo "  git remote set-url origin git@github.com:realplayerc4/nav24r.git"
echo "  git push origin main"

exit 1