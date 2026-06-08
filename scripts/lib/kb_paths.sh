#!/usr/bin/env bash
# 学习中心根目录（可被环境变量覆盖）
_kb_paths_resolve() {
  if [[ -n "${AI_LEARNING_CENTER:-}" && -d "$AI_LEARNING_CENTER" ]]; then
    echo "$AI_LEARNING_CENTER"
    return
  fi
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  echo "$(cd "$script_dir/../.." && pwd)"
}

KB_ROOT="$(_kb_paths_resolve)"
export KB_ROOT
