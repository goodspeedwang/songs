#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比云播放列表(music.163.com.txt)与本地曲库，找出"云上有、本地缺"的歌曲。
本地曲库 = 工作区所有 .mp3 文件(各专辑目录) + my.playlist.txt 的并集。

用法:
    python3 find_missing.py            # 打印缺失列表到终端
    python3 find_missing.py --write     # 同时写出 missing_songs.txt

依赖:
    pip install zhconv   (简繁转换)
"""
import re
import sys
import subprocess
import zhconv

ROOT = "/Users/goodspeed/Documents/code/private/songs.goodspeedwang.workers.dev"

# 云上文件名中明显是"同一首歌"但写法不同(异体字/错别字/翻唱版)，已确认本地有，排除
KNOWN_PRESENT = {171, 290, 347}

# 需要人工确认是否同一首的边界情况(留作备注，不影响缺失判定)
NOTES = {
    128: "本地有《好久》，可能是《好久不见》简写，请核对",
}


def norm(s: str) -> str:
    s = zhconv.convert(s, "zh-cn")
    s = s.lower()
    s = re.sub(r"\(live\)|\[live\]|（live）|\blive\b", " ", s)
    s = re.sub(r"\(dance\)|（dance）|\bdance\b", " ", s)
    s = re.sub(r"\bchaser\b|\btalking\b|\bcover\b|\bremix\b|\bdj\b|\bencore\b", " ", s)
    s = re.sub(r"\[[^\]]*\]|\([^)]*\)|（[^）]*）", " ", s)  # 去括号内容
    s = re.sub(r"[^0-9a-z\u4e00-\u9fff]", "", s)
    return s


has_cjk = lambda s: any("\u4e00" <= c <= "\u9fff" for c in s)


def load_cloud():
    out = []
    with open(f"{ROOT}/music.163.com.txt", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if line:
                out.append((i, re.sub(r"\.mp3$", "", line, flags=re.I)))
    return out


def load_local():
    names = []
    res = subprocess.run(
        ["bash", "-c",
         f"cd '{ROOT}' && find . -name '*.mp3' | sed 's#.*/##' | sed 's#\\.mp3$##'"],
        capture_output=True, text=True)
    names += [n.strip() for n in res.stdout.splitlines() if n.strip()]
    with open(f"{ROOT}/my.playlist.txt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                names.append(re.split(r"\s+-\s+", line)[0].strip())
    return names


def candidates(name: str):
    base = norm(name)
    parts = re.split(r"\s*[-_－]\s*|\s+", name)
    return [c for c in {base} | {norm(p) for p in parts} if c]


def build_local_index(names):
    idx = {}
    for n in names:
        nn = norm(n)
        if nn:
            idx.setdefault(nn, []).append(n)
    return idx


def is_present(name: str, local_norm: dict):
    cands = candidates(name)
    for c in cands:
        if c in local_norm:
            return True
    for c in cands:
        if len(c) >= 4 or has_cjk(c):
            for ln in local_norm:
                if len(ln) >= 3 and (c in ln or ln in c):
                    return True
    return False


def main():
    write = "--write" in sys.argv
    cloud = load_cloud()
    local_norm = build_local_index(load_local())

    present, missing = [], []
    for idx, name in cloud:
        if idx in KNOWN_PRESENT:
            present.append((idx, name))
        elif is_present(name, local_norm):
            present.append((idx, name))
        else:
            missing.append((idx, name))

    missing.sort(key=lambda x: x[0])
    present.sort(key=lambda x: x[0])

    print(f"云清单总数: {len(cloud)}")
    print(f"本地已有:   {len(present)}")
    print(f"云上有/本地缺: {len(missing)}")
    if NOTES:
        print("\n[需人工确认]")
        for k, v in sorted(NOTES.items()):
            print(f"  [{k}] {v}")
    print(f"\n==== 缺失列表 (共 {len(missing)} 首) ====")
    for idx, name in missing:
        print(f"{idx}\t{name}.mp3")

    if write:
        with open(f"{ROOT}/missing_songs.txt", "w", encoding="utf-8") as out:
            out.write(f"# 云上有、本地缺的歌曲（共 {len(missing)} 首）\n")
            out.write("# 来源：music.163.com.txt 对比 (my.playlist.txt + 工作区 mp3 目录)\n")
            out.write("# 格式：行号 <TAB> 云清单原始文件名\n\n")
            for idx, name in missing:
                out.write(f"{idx}\t{name}.mp3\n")
        print(f"\n[已写出] missing_songs.txt ({len(missing)} 首)")


if __name__ == "__main__":
    main()
