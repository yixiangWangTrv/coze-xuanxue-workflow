#!/usr/bin/env python3
"""
创建 Coze 工作流导入包
将工作流 JSON 打包成可导入的 ZIP 格式
"""

import json
import struct
import zipfile
import os
import io
import sys

def create_coze_package(workflow_json_path: str, output_path: str, workflow_name: str):
    """
    创建 Coze 工作流导入包
    
    Args:
        workflow_json_path: 工作流 JSON 文件路径
        output_path: 输出 ZIP 文件路径
        workflow_name: 工作流名称
    """
    # 读取工作流 JSON
    with open(workflow_json_path, 'r', encoding='utf-8') as f:
        workflow_data = f.read()
    
    # 验证 JSON 格式
    try:
        json.loads(workflow_data)
    except json.JSONDecodeError as e:
        print(f"错误: 无效的 JSON 格式 - {e}")
        sys.exit(1)
    
    # 构建内部文件头
    # 格式: 二进制元数据 + "workflow" + 元数据 + 文件名 + JSON
    header = bytearray()
    
    # 二进制元数据 (固定格式)
    header.extend(b'\x01\x00\x00\x00\x00\x00\x00\x02\x00\x01\x08\x00\x00\x00\x00\x00')
    
    # 长度字节和 "workflow" 标记
    header.extend(b'\x01\x00')
    header.extend(b'workflow')
    
    # 元数据
    header.extend(b'\x02\x27\x00\x04\x1c\x01\x00\x00\x00')
    
    # 文件名 (带长度前缀)
    filename = f"{workflow_name}.json"
    filename_bytes = filename.encode('utf-8')
    header.extend(struct.pack('<I', len(filename_bytes)))
    header.extend(filename_bytes)
    
    # JSON 内容
    json_bytes = workflow_data.encode('utf-8')
    
    # 组合内部文件
    inner_file = bytes(header) + json_bytes
    
    # 创建外层 ZIP
    inner_filename = f"Workflow-{workflow_name}.zip"
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_filename, inner_file)
    
    print(f"已创建导入包: {output_path}")
    print(f"工作流名称: {workflow_name}")
    print(f"JSON 大小: {len(json_bytes)} 字节")
    print(f"ZIP 大小: {os.path.getsize(output_path)} 字节")


def create_sample_workflow():
    """
    创建示例工作流 JSON
    """
    workflow = {
        "edges": [
            {"sourceNodeID": "100001", "sourcePortID": "", "targetNodeID": "100002"},
            {"sourceNodeID": "100002", "sourcePortID": "", "targetNodeID": "900001"}
        ],
        "nodes": [
            {
                "blocks": [],
                "data": {
                    "nodeMeta": {
                        "description": "工作流的起始节点，用于设定启动工作流需要的信息",
                        "icon": "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Start-v2.jpg",
                        "subTitle": "",
                        "title": "开始"
                    },
                    "outputs": [
                        {
                            "description": "输入文本",
                            "name": "input_text",
                            "required": True,
                            "type": "string"
                        }
                    ],
                    "trigger_parameters": [
                        {
                            "description": "输入文本",
                            "name": "input_text",
                            "required": True,
                            "type": "string"
                        }
                    ]
                },
                "edges": None,
                "id": "100001",
                "meta": {
                    "position": {"x": 0, "y": 0}
                },
                "type": "start"
            },
            {
                "blocks": [],
                "data": {
                    "nodeMeta": {
                        "description": "大语言模型节点",
                        "icon": "",
                        "subTitle": "",
                        "title": "大模型"
                    },
                    "inputs": {
                        "prompt": "请处理以下文本: {{input_text}}",
                        "model": "doubao-pro"
                    }
                },
                "edges": None,
                "id": "100002",
                "meta": {
                    "position": {"x": 300, "y": 0}
                },
                "type": "llm"
            },
            {
                "blocks": [],
                "data": {
                    "nodeMeta": {
                        "description": "工作流的结束节点，用于设定工作流的输出信息",
                        "icon": "",
                        "subTitle": "",
                        "title": "结束"
                    },
                    "inputs": {
                        "output": "{{100002.output}}"
                    }
                },
                "edges": None,
                "id": "900001",
                "meta": {
                    "position": {"x": 600, "y": 0}
                },
                "type": "end"
            }
        ],
        "versions": {}
    }
    return workflow


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='创建 Coze 工作流导入包')
    parser.add_argument('--input', '-i', help='工作流 JSON 文件路径')
    parser.add_argument('--output', '-o', help='输出 ZIP 文件路径', default='workflow.zip')
    parser.add_argument('--name', '-n', help='工作流名称', default='my_workflow')
    parser.add_argument('--sample', action='store_true', help='创建示例工作流')
    
    args = parser.parse_args()
    
    if args.sample:
        # 创建示例工作流
        sample_path = 'sample_workflow.json'
        with open(sample_path, 'w', encoding='utf-8') as f:
            json.dump(create_sample_workflow(), f, ensure_ascii=False, indent=2)
        print(f"已创建示例工作流: {sample_path}")
        create_coze_package(sample_path, args.output, args.name)
    elif args.input:
        create_coze_package(args.input, args.output, args.name)
    else:
        parser.print_help()
