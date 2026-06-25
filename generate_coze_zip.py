#!/usr/bin/env python3
"""
生成 Coze 工作流导入 ZIP 包
将抖音玄学视频蒸馏项目转换为可导入的 ZIP 格式
"""
import sys
import os

# 添加 coze-workflow skill 的 scripts 目录到路径
sys.path.insert(0, os.path.expanduser('~/.config/opencode/skills/coze-workflow/scripts'))

from coze_yaml_builder import *
from build_coze_zip import pack_workflow

# 修复版本的 loop_node 函数，支持单节点循环
def fixed_loop_node(nid, title, ref_id, ref_path, inner_nodes_str, inner_edge_pairs, last_inner_id, x=0, y=0):
    """
    inner_edge_pairs: list of (src_id, tgt_id) tuples for inner connections between inner nodes
    注意：不包含循环节点本身的入口/出口边
    """
    # 入口边：循环节点 → 第一个内部节点
    first_inner_id = inner_edge_pairs[0][0] if inner_edge_pairs else last_inner_id
    inner_edges = f'        - source_node: "{nid}"\n          target_node: "{first_inner_id}"\n          source_port: loop-function-inline-output\n'
    
    # 内部节点之间的连接
    for src, tgt in inner_edge_pairs:
        inner_edges += f'        - source_node: "{src}"\n          target_node: "{tgt}"\n'
    
    # 出口边：最后一个内部节点 → 循环节点
    inner_edges += f'        - source_node: "{last_inner_id}"\n          target_node: "{nid}"\n          target_port: loop-function-inline-input\n'
    
    return f'''    - id: "{nid}"
      type: loop
      title: {title}
      icon: {ICON_LOOP}
      description: "用于通过设定循环次数和逻辑，重复执行一系列任务"
      position:
        x: {x}
        y: {y}
      canvas_position:
        x: {x - 200}
        y: {y + 200}
      parameters:
        loopCount:
            type: integer
            value:
                content: 10
                rawMeta:
                    type: 2
                type: literal
        loopType: array
        node_inputs:
            - name: input
              input:
                type: list
                items:
                    type: string
                    value: null
                value:
                    path: {ref_path}
                    ref_node: "{ref_id}"
        node_outputs:
            output:
                value:
                    type: list
                    items:
                        type: string
                        value: null
                    value:
                        path: output
                        ref_node: "{last_inner_id}"
        variableParameters: []
      nodes:
{inner_nodes_str}      edges:
{inner_edges}'''

# 读取代码节点内容
def read_file(path):
    with open(os.path.join(os.path.dirname(__file__), path), 'r', encoding='utf-8') as f:
        return f.read()

# 读取各个文件
video_analyzer_code = read_file('code_nodes/video_analyzer.py')
video_synthesizer_code = read_file('code_nodes/video_synthesizer.py')
style_translator_prompt = read_file('prompts/style_translator.md')
subtitle_splitter_prompt = read_file('prompts/subtitle_splitter.md')

# ============================================================
# 阶段一：风格蒸馏工作流
# ============================================================
def generate_workflow_1():
    """生成阶段一：风格蒸馏工作流"""
    nodes = ''
    edges = ''

    # 节点1：开始节点
    nodes += start_node("100001", {"video_url": "string"})

    # 节点2：代码节点 - 视频分析
    # 注意：Coze 代码节点不支持 subprocess，需要简化代码
    simplified_analyzer = '''
def main(video_url: str) -> dict:
    """
    视频风格分析节点
    注意：在 Coze 环境中，需要使用插件替代 yt-dlp 和 ffmpeg
    这里提供简化版本，实际部署时需要对接 Coze 的视频处理插件
    """
    # 由于 Coze 代码节点不支持 subprocess，这里返回示例数据
    # 实际使用时需要对接 Coze 的视频下载和处理插件
    return {
        "visual": {
            "tone": "暗琥珀色调，暖色系 R>G>B",
            "avg_rgb": {"R": 58, "G": 46, "B": 31},
            "brightness": {"value": 45, "level": 2},
            "dark_pixel_ratio": "65%",
            "warm_pixel_ratio": "28%"
        },
        "audio": {
            "pitch": "~237Hz (偏高男声)",
            "spectral_centroid": "1834Hz",
            "avg_zero_crossing_rate": "0.089",
            "pace": "舒缓平稳"
        },
        "scenes": {
            "scene_count": 3,
            "transitions": [{"frame": 5, "type": "黑场过渡"}],
            "transition_style": "黑场淡入淡出"
        }
    }
'''

    nodes += code_node(
        nid="100002",
        title="视频分析",
        code_str=simplified_analyzer,
        language=3,  # Python
        inputs_list=[{"name": "video_url"}],
        outputs_list=[{"name": "output", "type": "object"}],
        ref_id="100001",
        ref_path="video_url",
        x=300, y=0
    )

    # 节点3：LLM节点 - 风格翻译
    nodes += llm_node(
        nid="100003",
        title="风格翻译",
        sys_prompt=style_translator_prompt,
        prompt="{{100002.output}}",
        ref_id="100002",
        ref_path="output",
        x=600, y=0
    )

    # 节点4：结束节点
    nodes += end_node("900001", "100003", "output", x=900)

    # 边
    edges = edge("100001", "100002")
    edges += edge("100002", "100003")
    edges += edge("100003", "900001")

    return nodes, edges


# ============================================================
# 阶段二：视频生成工作流
# ============================================================
def generate_workflow_2():
    """生成阶段二：视频生成工作流（使用 100001-100005 节点 ID）"""
    nodes = ''
    edges = ''

    # 节点1：开始节点
    nodes += start_node("100001", {"subtitle_text": "string", "style_id": "string"})

    # 节点2：知识库节点 - 加载风格档案
    nodes += knowledge_node(
        nid="100002",
        title="加载风格档案",
        ref_id="100001",
        ref_path="style_id",
        x=300, y=0
    )

    # 节点3：LLM节点 - 字幕拆分
    simple_subtitle_prompt = "你是玄学短视频分镜导演。将字幕拆分为3-5个段落，每段6-10秒。输出JSON数组：[{segment_index, subtitle_text, video_prompt, estimated_duration}]。使用dark amber tones, candle-like warm glow, low-key cinematic lighting, zen spiritual atmosphere作为前缀。"

    nodes += llm_node(
        nid="100003",
        title="字幕拆分",
        sys_prompt=simple_subtitle_prompt,
        prompt="{{100001.subtitle_text}}",
        ref_id="100002",
        ref_path="outputList",
        x=600, y=0
    )

    # 节点4：循环节点 - 并行生成视频和TTS
    inner_nodes = inner_llm_node(
        nid="301001",
        title="生成视频提示词",
        sys_prompt="你是视频提示词生成专家，根据分镜描述生成即梦/Jimeng文生视频的英文提示词。",
        prompt="{{input}}",
        ref_id="100004",
        ref_path="input",
        x=180, y=0
    )

    nodes += fixed_loop_node(
        nid="100004",
        title="并行生成",
        ref_id="100003",
        ref_path="output",
        inner_nodes_str=inner_nodes,
        inner_edge_pairs=[],
        last_inner_id="301001",
        x=900, y=0
    )

    # 节点5：代码节点 - 视频合成
    simplified_synthesizer = '''
def main(segments: list, style_profile: dict) -> dict:
    """
    视频合成节点
    注意：在 Coze 环境中，需要使用视频合成插件
    这里提供简化版本，实际部署时需要对接 Coze 的视频合成 API
    """
    return {
        "output_video_url": "https://example.com/output.mp4",
        "segments_count": len(segments),
        "message": "视频合成完成（示例）"
    }
'''

    nodes += code_node(
        nid="100005",
        title="视频合成",
        code_str=simplified_synthesizer,
        language=3,
        inputs_list=[
            {"name": "segments"},
            {"name": "style_profile"}
        ],
        outputs_list=[{"name": "output_video_url", "type": "string"}],
        ref_id="100004",
        ref_path="output",
        x=1200, y=0
    )

    # 节点6：结束节点
    nodes += end_node("900001", "100005", "output_video_url", x=1500)

    # 边
    edges = edge("100001", "100002")
    edges += edge("100002", "100003")
    edges += edge("100003", "100004")
    edges += edge("100004", "100005", "loop-output")
    edges += edge("100005", "900001")

    return nodes, edges


if __name__ == "__main__":
    os.makedirs('/tmp/coze-workflow', exist_ok=True)

    # 生成阶段一：风格蒸馏
    print("生成阶段一：风格蒸馏工作流...")
    nodes1, edges1 = generate_workflow_1()
    build_workflow(
        name="xuanxue_style_distill",
        wf_id="7585079438426600001",
        desc="抖音玄学视频风格蒸馏：从视频中提取视觉/音频风格参数，生成风格档案",
        nodes_str=nodes1,
        edges_str=edges1,
        out_path="./Workflow-xuanxue_style_distill-draft-0001.zip"
    )

    # 生成阶段二：视频生成
    print("\n生成阶段二：视频生成工作流...")
    nodes2, edges2 = generate_workflow_2()
    build_workflow(
        name="xuanxue_video_gen",
        wf_id="7585079438426600002",
        desc="抖音玄学视频生成：使用风格档案和字幕文本生成短视频",
        nodes_str=nodes2,
        edges_str=edges2,
        out_path="./Workflow-xuanxue_video_gen-draft-0001.zip"
    )

    print("\n✅ 生成完成！")
    print("导入方法：")
    print("1. 登录 https://www.coze.cn/space")
    print("2. 进入个人空间 → 资源库")
    print("3. 点击右上角 '导入' 按钮")
    print("4. 上传生成的 ZIP 文件")
