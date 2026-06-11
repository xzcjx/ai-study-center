#!/usr/bin/env python3
"""
腾讯滑块 TDC collect 计算器 — Python 端调用

用法:
  from collect_endpoint.calculate import get_collect
  collect = get_collect("tdc.js")  # 传入 tdc.js 文件路径

依赖:
  - Node.js >= 18
  - tdc.js 文件（从腾讯滑块页面获取）
"""

import subprocess
import json
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECT_JS = os.path.join(HERE, "collect.js")


def get_collect(tdc_path: str, profile: dict = None, timeout: int = 30) -> str:
    """
    从 tdc.js 计算 collect 字段

    Args:
      tdc_path:  tdc.js 文件路径
      profile:   指纹 profile（None = 自动生成随机指纹）
      timeout:   Node.js 执行超时(秒)

    Returns:
      collect 字段值 (Base64 + XTEA 加密的字符串)
    """
    cmd = ["node", COLLECT_JS, f"--tdc={tdc_path}"]

    if profile:
        # 将 profile 写入临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(profile, f)
            profile_path = f.name
        cmd.append(f"--profile={profile_path}")
    else:
        cmd.append("--auto")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=HERE,
        )
    finally:
        if profile:
            os.unlink(profile_path)

    if result.returncode != 0:
        raise RuntimeError(
            f"collect.js failed:\nSTDERR: {result.stderr}\nSTDOUT: {result.stdout}"
        )

    # stdout 就是 collect 字段
    return result.stdout.strip()


def set_xtra_key(key: list):
    """
    设置 XTEA 加密密钥（从 tdc.js 中提取后设置）

    Args:
      key: [k0, k1, k2, k3] 四个 uint32
    """
    import os

    # 写入环境变量（简单方案）
    key_str = ",".join(str(k) for k in key)
    os.environ["TDC_XTEA_KEY"] = key_str


# ====== 命令行入口 ======
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python calculate.py <tdc.js> [--auto] [--profile=profile.json]")
        print(f"  或者: python calculate.py <tdc.js> --key=k0,k1,k2,k3")
        sys.exit(1)

    tdc_file = sys.argv[1]
    profile = None

    for arg in sys.argv[2:]:
        if arg.startswith("--profile="):
            with open(arg.split("=")[1]) as f:
                profile = json.load(f)
        elif arg.startswith("--key="):
            key = [int(k, 0) for k in arg.split("=")[1].split(",")]
            set_xtra_key(key)

    collect = get_collect(tdc_file, profile)
    print(collect)
