#!/usr/bin/env bash
# ==============================================================================
# mihomo-cli 安装脚本
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_NAME="mihomo-cli"
SRC_BIN="$SCRIPT_DIR/$BIN_NAME"

TARGET_DIR="${HOME}/.local/bin"

if [[ ! -f "$SRC_BIN" ]]; then
  echo "错误: 未在 $SCRIPT_DIR 下找到 $BIN_NAME" >&2
  exit 1
fi

chmod +x "$SRC_BIN"

mkdir -p "$TARGET_DIR"
ln -sf "$SRC_BIN" "$TARGET_DIR/$BIN_NAME"

echo "✔ 已成功将 $BIN_NAME 软链接至: $TARGET_DIR/$BIN_NAME"

# 检查 PATH 是否包含 TARGET_DIR
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
  echo ""
  echo "提示: $TARGET_DIR 不在当前 PATH 中，请将以下内容添加到您的 ~/.bashrc 或 ~/.zshrc:"
  echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
else
  echo "✔ 当前终端可以直接运行命令: mihomo-cli"
fi
