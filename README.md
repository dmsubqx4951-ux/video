# 两千载，弹指之间

[下载新版视频（MP4）](https://github.com/dmsubqx4951-ux/video/raw/refs/heads/main/deliveries/zhuge-shanghai-2026-lively.mp4)，下载后用手机相册或系统播放器打开。

新版调整了配音、人物表演与交流节奏：取消对白拉长，换用本地 Kokoro 中文男声；诸葛亮有侧头、点头、观察手机与抬扇反应，年轻人有说话和点头动作，路人有步态，片尾使用侧面转身姿态。保留圆润亲民的诸葛亮形象。

[前一版视频](https://github.com/dmsubqx4951-ux/video/raw/refs/heads/main/deliveries/zhuge-shanghai-2026-cute.mp4)也保留在仓库中。

用 Python 代码生成的 **36 秒卡通短片**：2026 年夜晚，诸葛亮出现在上海陆家嘴人行天桥。

所有场景、人物、羽扇、手机、车辆与镜头运动均由代码绘制；无素材图片、无图像或视频生成 API。中文对白在本机用 sherpa-onnx / Kokoro v1.0 合成，环境音与片尾弦乐由 NumPy/SciPy 生成。

## 运行

要求 Python 3.12+、FFmpeg（含 libx264）、Noto CJK 字体。本云环境已经提供这些基础工具。模型下载约 221 MB，渲染后续完全在本机运行。

```bash
cd /workspace/video
bash setup.sh
.venv/bin/python film.py --stills
.venv/bin/python film.py
.venv/bin/python film.py --output output/zhuge-shanghai-2026-lively.mp4
```

主要产物：

- `output/zhuge-shanghai-2026.mp4`：1280×720，24 fps，H.264 / AAC，双声道，36 秒。
- `output/zhuge-shanghai-2026-lively.mp4`：配音节奏和人物动作改进的新版（使用上面的 `--output` 命令）。
- `output/storyboard.jpg`：六幅关键画面预览。
- `output/soundtrack.wav`：48 kHz 双声道音轨。
- `output/dialogue-timing.json`：对白的实际入点、出点。

视频包含四个镜头：0–8 秒初见未来、8–16 秒此乃何方城池、16–28 秒手机传讯、28–36 秒回望城市。20.3–23 秒为第三镜头中的手机特写。开头先响起环境音后渐亮；末尾字幕淡入、画面渐暗，城市音再延续短暂片刻。

`film.py` 管理人物、城市绘制、表情、羽扇动作、字幕和镜头；`audio.py` 管理两种男声、对白停顿、车流、鸣笛、脚步、手机提示音和片尾拨弦。可以在这些文件里调整场景、颜色、台词和时间。

新版诸葛亮采用饱满脸颊、柔和眉毛、带高光的棕色眼睛、淡淡腮红和较短的圆润胡须。惊讶、警觉、好奇、沉思各有不同表情；交流时带轻微笑意。

## 依赖与可复现性

`requirements.txt` 固定 Python 依赖版本；`setup.sh` 从 sherpa-onnx 官方 GitHub 发布下载模型，并验证固定 SHA-256。模型来源：

https://github.com/k2-fsa/sherpa-onnx/releases/tag/tts-models

`assets/`、`.venv/` 和 `output/` 是可重新生成的本地产物，已在 `.gitignore` 中排除。语音首次生成后会缓存，缓存键包含模型、音色、语速与文本。较短台词保留自然时长，只有超出镜头上限的台词才会用保持音高的加速来适配；不再减速填满镜头。音效使用固定随机种子。没有后台服务，未来任务需要重新执行渲染命令。

## 验证

```bash
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,sample_rate,channels -of json output/zhuge-shanghai-2026.mp4
ffmpeg -v error -i output/zhuge-shanghai-2026.mp4 -f null -
```

检查预期时长 36 秒，视频 H.264 / 1280×720 / 24 fps，音频 AAC / 48 kHz / 双声道，并确认解码无错误。
