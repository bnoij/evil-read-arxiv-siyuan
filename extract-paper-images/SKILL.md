---
name: extract-paper-images
description: 从 arXiv、公开 PDF 或本地 PDF 提取研究图片并上传到思源 assets，供 Kimi 精读和日报使用。Use when a research workflow needs embeddable figures.
---

# 提取并上传研究图片

1. 接受合法 arXiv ID/链接、公开 PDF URL 或本地 PDF。其他网页先由 `paper-analyze/scripts/resolve_source.py` 解析。
2. 在系统临时目录创建 `WORK/images`，不把 PDF 或图片写入插件目录：

```bash
python "$SKILL_DIR/scripts/extract_images.py" "<source>" "$WORK/images" "$WORK/images/index.md"
```

3. 检查 index 和实际图片。优先架构、方法、主要结果和消融图，过滤 logo、小图标、重复内容、裁剪错误和不可读图片。
4. 上传筛选后的 PNG/JPEG/GIF/WebP：

```bash
python "$SKILL_DIR/scripts/upload_assets.py" \
  --assets-dir "/assets/" \
  "$WORK/images/figure-1.png" "$WORK/images/figure-2.png"
```

5. 返回上传后的 `assets/...` 路径、数量和图意。正文使用 `![图意](assets/...)`，不要使用其他笔记软件的嵌入语法。

上传失败时报告具体文件和错误，不把本地临时路径写进最终笔记。只清理本次临时文件，不删除已有 assets。
