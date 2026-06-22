# 抖音玄学视频蒸馏 - Coze工作流配置指南

## 一键导入（推荐）

### 第一步：下载导入包

下载 `dist/抖音玄学视频蒸馏工作流.zip` 文件。

### 第二步：导入到 Coze

1. 登录 [Coze 官网](https://www.coze.cn/space)，进入个人空间
2. 在左侧菜单选择 **"资源库"**
3. 点击右上角 **"导入"** 按钮
4. 上传 `抖音玄学视频蒸馏工作流.zip` 文件
5. 点击 **"导入"** 确认

导入成功后，工作流会出现在资源库列表中。

### 第三步：配置依赖

1. **开通扣子会员**：确保有即梦/Jimeng文生视频和TTS的使用额度
2. **创建知识库**：
   - 名称：`xuanxue_style_profiles`
   - 字段：`id`, `name`, `profile`(json类型)
   - 导入 `profiles/jingchen_yinzhe.json`

---

## 手动配置

如果需要手动配置，请参考以下步骤。

---

## 阶段一：风格蒸馏工作流

### 节点1：开始节点
- 输入参数：`video_url` (string) — 抖音视频链接

### 节点2：代码节点 — 视频分析
- 代码来源：`code_nodes/video_analyzer.py`
- Coze环境适配：如不支持yt-dlp，先配置视频下载插件，将下载后的URL传入分析节点
- 输出：`style_params` (JSON)

### 节点3：LLM节点 — 风格翻译
- 模型：GPT-4 / Claude / Doubao Pro
- 提示词：使用 `prompts/style_translator.md` 的内容
- 输入变量映射：`style_params` → `{{style_params}}`
- 输出：`style_profile` (JSON)

### 节点4：知识库写入节点
- 操作：写入 `xuanxue_style_profiles`
- 映射：`style_profile.name` → `name`, `style_profile` → `profile`

### 节点5：结束节点
- 输出：风格档案摘要

---

## 阶段二：视频生成工作流

### 节点1：开始节点
- 输入参数：
  - `subtitle_text` (string) — 字幕文本
  - `style_id` (string) — 风格档案ID（默认：jingchen_yinzhe）

### 节点2：知识库读取节点
- 操作：从 `xuanxue_style_profiles` 查询
- 过滤器：`id = {{style_id}}`
- 输出：`style_profile` (JSON)

### 节点3：LLM节点 — 字幕拆分与分镜
- 模型：GPT-4 / Claude / Doubao Pro
- 提示词：使用 `prompts/subtitle_splitter.md` 的内容
- 输入变量映射：
  - `subtitle_text` → `{{subtitle_text}}`
  - `style_profile` → `{{style_profile}}`
- 输出：`segments` (JSON数组)

### 节点4：循环节点（并行处理每个段落）
- 循环对象：`segments` 数组
- 最大并行数：5

**子节点4a：文生视频节点**
- 插件：即梦/Jimeng 文生视频
- 参数：
  - prompt: `style_profile.prompt_prefix` + `segment.video_prompt`
  - negative_prompt: `style_profile.negative_prompt`
  - 分辨率：720x1280
  - 时长：取 `segment.estimated_duration`（上限10s）
  - 风格：写实
- 输出：`video_url`

**子节点4b：TTS节点**
- 插件：火山引擎 TTS
- 参数（从 `style_profile.tts_settings` 读取）：
  - text: `segment.subtitle_text`
  - voice: 深沉男声
  - speed: 0.85
  - pitch: +1
- 输出：`audio_url`, `audio_duration`

### 节点5：代码节点 — 结果收集
- 收集循环节点的输出，组装 `final_segments` 数组
- 每项：`{video_url, audio_url, subtitle_text, audio_duration}`

### 节点6：视频合成节点
- 方案A：使用扣子视频合成插件
- 方案B：代码节点调用外部API（Shotstack等）
- 方案C：输出素材包 + 合成指引
- 输入：`final_segments`, `style_profile`
- 输出：`output_video_url`

### 节点7：结束节点
- 输出：`output_video_url`（MP4下载链接）

---

## 测试流程

1. **单元测试每个节点**：
   - 视频分析节点：用真实抖音视频测试
   - LLM节点：用测试字幕验证输出JSON格式
   - TTS节点：用不同文本测试音色效果
   - 文生视频节点：用测试提示词验证画面质量

2. **端到端测试**：
   - 输入测试字幕："万物皆有裂痕，那是光照进来的地方"
   - 验证：生成的视频画面风格、音频节奏、字幕位置均与净尘隐者风格一致

3. **质量检查清单**：
   - [ ] 画面色调为暗琥珀色
   - [ ] 转场为黑场淡入淡出
   - [ ] 字幕白色居中底部
   - [ ] 配音语速舒缓（约0.85x）
   - [ ] 总时长在30-60秒范围
   - [ ] 输出为720x1280竖屏
