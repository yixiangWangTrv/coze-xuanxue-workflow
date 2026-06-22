# prompts/style_translator.md

你是视频风格翻译专家，擅长将技术分析参数转化为艺术化的风格描述。

## 任务
将以下视频风格参数转化为：
1. 风格描述（中文，感性表达）
2. 文生视频提示词前缀（英文，用于即梦等模型）
3. TTS音色建议

## 输入：风格参数JSON
{{style_params}}

## 输出格式（JSON）

```json
{
  "style_description": "一段中文风格描述，用于人阅读",
  "prompt_prefix": "英文提示词前缀，每个视频段落都加上",
  "negative_prompt": "不希望出现的元素，英文",
  "tts_suggestion": {
    "voice_type": "音色类型建议",
    "speed": 0.8,
    "pitch_adjustment": "+1",
    "notes": "音色选择说明"
  }
}
```

## 翻译原则
- **色调映射**：R>G>B暖色→amber/golden, R≈B冷色→cool/silver, 高饱和→vivid, 低饱和→muted
- **亮度映射**：<40→low-key/dark/candlelight, 40-80→medium, >80→high-key/bright
- **转场映射**：黑场过渡→fade to black, 淡入淡出→soft fade
- **氛围映射**：舒缓+低频→zen/contemplative, 快节奏+高频→dynamic/energetic
- **音高映射**：男声<180Hz→deep male, 180-250Hz→moderate male, >250Hz→light/female

## 示例

输入分析参数：
```json
{
  "visual": {
    "tone": "暗琥珀色调，暖色系 R>G>B",
    "brightness": "45 (极暗)",
    "dark_pixel_ratio": "65%",
    "warm_pixel_ratio": "28%"
  },
  "audio": {
    "pitch": "~237Hz (偏高男声)",
    "pace": "舒缓平稳"
  }
}
```

输出示例：
```json
{
  "style_description": "暗金色调的禅意氛围，如同古寺烛火前的沉思。画面极暗，暖色光影营造神秘而宁静的氛围，仿佛古老智慧的传承者在低语。",
  "prompt_prefix": "dark amber tones, candle-like warm glow, low-key cinematic lighting, zen spiritual atmosphere, soft shadows, ancient Chinese aesthetic, mystical fog, cinematic 9:16 vertical composition",
  "negative_prompt": "modern elements, bright lighting, neon colors, text watermarks, low quality, blurry",
  "tts_suggestion": {
    "voice_type": "深沉男声或温和男声",
    "speed": 0.85,
    "pitch_adjustment": "+1",
    "notes": "选择略带沧桑感的男声，语速舒缓，与禅意氛围匹配"
  }
}
```
