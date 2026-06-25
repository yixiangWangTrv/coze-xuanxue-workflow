#!/usr/bin/env python3
"""
创建 Coze 工作流导入包
将工作流 JSON 打包成可导入的 ZIP 格式

格式（基于参考模板分析）：
- 外层 ZIP 包含一个内层文件
- 内层文件结构：Header(35+N字节) + JSON + Separator(9字节) + MANIFEST.yml
- N = 文件名的精确字节数
"""

import json
import struct
import zipfile
import os
import sys

# 固定分隔符（JSON 和 MANIFEST.yml 之间）
SEPARATOR = b'\x02\x0c\x00\x22\x01\x00\x00\x00\x00'

def create_coze_package(workflow_json_path: str, output_path: str, workflow_name: str, draft_id: str = None):
    """
    创建 Coze 工作流导入包
    
    Args:
        workflow_json_path: 工作流 JSON 文件路径
        output_path: 输出 ZIP 文件路径
        workflow_name: 工作流名称（不含 -draft 后缀）
        draft_id: 草稿 ID（可选，用于生成正确的文件名格式）
    """
    # 读取工作流 JSON
    with open(workflow_json_path, 'r', encoding='utf-8') as f:
        workflow_obj = json.load(f)
    
    # 转换为紧凑格式（无换行无缩进）
    workflow_data = json.dumps(workflow_obj, ensure_ascii=False, separators=(',', ':'))
    json_bytes = workflow_data.encode('utf-8')
    
    # 文件名（参考模板格式：{name}-draft.json）
    filename = f"{workflow_name}-draft.json"
    filename_bytes = filename.encode('utf-8')
    N = len(filename_bytes)  # 文件名的精确字节数
    
    # 构建 Header（共 35+N 字节）
    header = bytearray()
    
    # 0-17: 18字节固定前缀
    header.extend(b'\x01\x00\x00\x00\x00\x00\x00\x02\x00\x01\x08\x00\x00\x00\x00\x00\x01\x00')
    
    # 18-25: 8字节 magic "workflow"
    header.extend(b'workflow')
    
    # 26: 1字节类型标识
    header.extend(b'\x02')
    
    # 27-28: 2字节 N（文件名长度，little-endian uint16）
    header.extend(struct.pack('<H', N))
    
    # 29-34: 6字节固定元数据
    header.extend(b'\x04\x1c\x01\x00\x00\x00')
    
    # 35~34+N: 文件名
    header.extend(filename_bytes)
    
    # MANIFEST.yml 内容
    # 生成随机 ID（参考模板格式）
    import random
    workflow_id = str(random.randint(1000000000000000000, 9999999999999999999))
    dev_id = str(random.randint(1000000000000000000, 9999999999999999999))
    commit_id = f"Bot_{workflow_id}_Dev_{dev_id}_{workflow_id}"
    
    manifest_content = f"""MANIFEST.ymltype: Workflow
version: 1.0.0
main:
    id: {workflow_id}
    name: {workflow_name}
    desc: {workflow_name}
    icon: plugin_icon/workflow.png
    version: ""
    flowMode: 0
    commitId: {commit_id}
"""
    manifest_bytes = manifest_content.encode('utf-8')
    
    # 组合内部文件：Header + JSON + Separator + MANIFEST.yml
    inner_file = bytes(header) + json_bytes + SEPARATOR + manifest_bytes
    
    # 创建外层 ZIP
    # 文件名格式: Workflow-{name}-draft-{id}.zip 或 Workflow-{name}.zip
    if draft_id:
        inner_filename = f"Workflow-{workflow_name}-draft-{draft_id}.zip"
    else:
        inner_filename = f"Workflow-{workflow_name}.zip"
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_filename, inner_file)
    
    print(f"已创建导入包: {output_path}")
    print(f"工作流名称: {workflow_name}")
    print(f"文件名: {filename}")
    print(f"文件名长度 (N): {N}")
    print(f"JSON 字节数: {len(json_bytes)}")
    print(f"Header 大小: {len(header)} 字节")
    print(f"内部文件总大小: {len(inner_file)} 字节")
    print(f"ZIP 大小: {os.path.getsize(output_path)} 字节")


def extract_and_inspect(zip_path: str):
    """
    解压并检查 ZIP 包结构（用于调试）
    """
    print(f"\n检查 ZIP 包: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        print(f"外层 ZIP 包含文件: {zf.namelist()}")
        
        # 读取内层文件
        inner_name = zf.namelist()[0]
        inner_data = zf.read(inner_name)
        
        print(f"\n内层文件: {inner_name}")
        print(f"内层文件大小: {len(inner_data)} 字节")
        
        # 解析 Header
        if len(inner_data) < 35:
            print("错误：文件太小，无法包含完整 Header")
            return
        
        # 检查固定前缀
        expected_prefix = b'\x01\x00\x00\x00\x00\x00\x00\x02\x00\x01\x08\x00\x00\x00\x00\x00\x01\x00'
        actual_prefix = inner_data[0:18]
        print(f"\n固定前缀匹配: {actual_prefix == expected_prefix}")
        if actual_prefix != expected_prefix:
            print(f"期望: {expected_prefix.hex()}")
            print(f"实际: {actual_prefix.hex()}")
        
        # 检查 magic
        magic = inner_data[18:26]
        print(f"Magic: {magic}")
        
        # 检查类型标识
        type_id = inner_data[26]
        print(f"类型标识: 0x{type_id:02x}")
        
        # 解析 N（文件名长度）
        N = struct.unpack('<H', inner_data[27:29])[0]
        print(f"文件名长度 (N): {N}")
        
        # 检查固定元数据
        expected_meta = b'\x04\x1c\x01\x00\x00\x00'
        actual_meta = inner_data[29:35]
        print(f"固定元数据匹配: {actual_meta == expected_meta}")
        
        # 提取文件名
        filename_start = 35
        filename_end = filename_start + N
        if filename_end > len(inner_data):
            print("错误：文件名超出文件范围")
            return
        filename = inner_data[filename_start:filename_end].decode('utf-8')
        print(f"文件名: {filename}")
        
        # JSON 起始位置
        json_start = filename_end
        
        # 找到 JSON 结束位置（通过匹配大括号）
        brace_count = 0
        json_end = -1
        for i in range(json_start, len(inner_data)):
            b = inner_data[i]
            if b == ord('{'):
                brace_count += 1
            elif b == ord('}'):
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break
        
        if json_end == -1:
            print("错误：未找到 JSON 结束位置")
            return
        
        json_data = inner_data[json_start:json_end]
        print(f"JSON 大小: {len(json_data)} 字节")
        
        # 尝试解析 JSON
        try:
            json_obj = json.loads(json_data)
            print(f"JSON 解析成功，包含 {len(json_obj.get('nodes', []))} 个节点")
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
        
        # 检查分隔符
        separator_start = json_end
        separator_end = separator_start + 9
        if separator_end <= len(inner_data):
            separator = inner_data[separator_start:separator_end]
            print(f"分隔符: {separator.hex()}")
            print(f"分隔符匹配: {separator == SEPARATOR}")
        
        # 检查 MANIFEST.yml
        manifest_start = separator_end
        if manifest_start < len(inner_data):
            manifest_data = inner_data[manifest_start:]
            print(f"MANIFEST.yml 大小: {len(manifest_data)} 字节")
            try:
                manifest_text = manifest_data.decode('utf-8')
                print(f"MANIFEST.yml 内容:\n{manifest_text}")
            except:
                print("MANIFEST.yml 解码失败")


if __name__ == "__main__":
    import argparse
    import random
    
    parser = argparse.ArgumentParser(description='创建 Coze 工作流导入包')
    parser.add_argument('--input', '-i', help='工作流 JSON 文件路径')
    parser.add_argument('--output', '-o', help='输出 ZIP 文件路径', default='workflow.zip')
    parser.add_argument('--name', '-n', help='工作流名称', default='my_workflow')
    parser.add_argument('--draft', '-d', help='草稿 ID（可选，用于生成正确的文件名格式）')
    parser.add_argument('--inspect', help='检查现有 ZIP 包结构')
    
    args = parser.parse_args()
    
    if args.inspect:
        extract_and_inspect(args.inspect)
    elif args.input:
        draft_id = args.draft or str(random.randint(1000, 9999))
        create_coze_package(args.input, args.output, args.name, draft_id)
    else:
        parser.print_help()