import pandas as pd
import os
import re
import argparse

# 标准化函数
def normalize_text(text):
    if pd.isna(text) or text == '':
        return ''
    
    # 转换为字符串
    text = str(text)
    
    # 去空格
    text = text.strip()
    
    # 全半角统一
    text = text.replace('，', ',').replace('。', '.').replace('；', ';').replace('：', ':')
    text = text.replace('（', '(').replace('）', ')').replace('【', '[').replace('】', ']')
    
    # 大小写统一（这里保持原样，因为品牌名可能有大小写区分）
    # text = text.lower()
    
    # 去除多余的空白字符
    text = re.sub(r'\s+', ' ', text)
    
    return text

# 拆分多值函数
def split_values(text, separator=','):
    if pd.isna(text) or text == '':
        return []
    
    values = [v.strip() for v in str(text).split(separator)]
    return [v for v in values if v != '']

# 读取文件
def read_file(file_path):
    return pd.read_csv(file_path)

# 分析函数
def analyze_manu_enterprise_brand(df):
    groups = df.groupby('manu_no')
    results = []
    
    for manu_no, group in groups:
        # 标准化处理
        normalized_ent = group['enterprise'].apply(normalize_text)
        normalized_brand = group['brand'].apply(normalize_text)
        
        # 拆分多值
        all_ents = []
        all_brands = []
        
        for ent in normalized_ent:
            all_ents.extend(split_values(ent))
        
        for brand in normalized_brand:
            all_brands.extend(split_values(brand))
        
        # 去除空值
        all_ents = [e for e in all_ents if e != '']
        all_brands = [b for b in all_brands if b != '']
        
        # 计算唯一性
        ent_unique = len(set(all_ents))
        brand_unique = len(set(all_brands))
        
        # 计算存在性
        both_present = ((normalized_ent != '') & (normalized_brand != '')).sum()
        ent_present = (normalized_ent != '').sum()
        brand_present = (normalized_brand != '').sum()
        total_records = len(group)
        
        # 计算比例
        both_present_ratio = both_present / total_records if total_records > 0 else 0
        ent_present_ratio = ent_present / total_records if total_records > 0 else 0
        brand_present_ratio = brand_present / total_records if total_records > 0 else 0
        
        # 类型划分
        type_case = ""
        status = ""
        action = ""
        
        if ent_unique == 0 and brand_unique == 0:
            # 类型C：无有效数据
            type_case = "C"
            status = "C_NO_INFO"
            action = "无法填"
        elif ent_unique > 1:
            # 类型D：企业多样
            type_case = "D"
            status = "D_CONFLICT"
            action = "排除"
        elif ent_unique == 1:
            if brand_unique == 1:
                # 类型A：企业唯一，品牌唯一
                if len(all_ents) > 0 and len(all_brands) > 0:
                    if set(all_ents) == set(all_brands):
                        # 类型A1：企业和品牌相同
                        type_case = "A1"
                        status = "A1_OK_FILL_BOTH"
                        action = "填enterprise+brand"
                    else:
                        # 类型A2：企业和品牌不同
                        type_case = "A2"
                        status = "A2_CONFLICT"
                        action = "排除"
                else:
                    # 信息不足
                    type_case = "C"
                    status = "C_NO_INFO"
                    action = "无法填"
            else:
                # 类型B：企业唯一，品牌多样
                type_case = "B"
                status = "B_FILL_ENT_ONLY"
                action = "只填enterprise"
        else:
            # 其他情况
            type_case = "C"
            status = "C_NO_INFO"
            action = "无法填"
        
        # 置信度计算
        confidence = 0
        if type_case == "A1":
            # A1的置信度
            if total_records >= 3 and both_present >= 2:
                confidence = 0.9
            elif total_records >= 2 and both_present >= 1:
                confidence = 0.7
            else:
                confidence = 0.5
        elif type_case == "B":
            # B的置信度（只填enterprise）
            if total_records >= 3 and ent_present >= 2:
                confidence = 0.8
            elif total_records >= 2 and ent_present >= 1:
                confidence = 0.6
            else:
                confidence = 0.4
        
        # 获取主要值
        main_enterprise = list(set(all_ents))[0] if ent_unique == 1 and len(all_ents) > 0 else ''
        main_brand = list(set(all_brands))[0] if brand_unique == 1 and len(all_brands) > 0 else ''
        
        # 计算可填充记录数
        empty_ent = (normalized_ent == '').sum()
        empty_brand = (normalized_brand == '').sum()
        
        results.append({
            'manu_no': manu_no,
            'manu_name': group['manu_name'].iloc[0] if not group.empty else '',
            'total_records': total_records,
            'ent_unique': ent_unique,
            'brand_unique': brand_unique,
            'both_present': both_present,
            'ent_present': ent_present,
            'brand_present': brand_present,
            'both_present_ratio': both_present_ratio,
            'ent_present_ratio': ent_present_ratio,
            'brand_present_ratio': brand_present_ratio,
            'empty_ent': empty_ent,
            'empty_brand': empty_brand,
            'main_enterprise': main_enterprise,
            'main_brand': main_brand,
            'type_case': type_case,
            'status': status,
            'action': action,
            'confidence': confidence
        })
    
    return pd.DataFrame(results)

# 主函数
def main():
    parser = argparse.ArgumentParser(description='增强版企业和品牌数据分析')
    parser.add_argument('--input', default='../data/ner_key_product_info_top95.csv', help='输入文件路径')
    parser.add_argument('--output', default='../output/analysis_results.csv', help='输出分析文件路径')
    args = parser.parse_args()
    
    # 检查输入文件
    # 使用基于脚本位置的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, args.input)
    if not os.path.exists(input_path):
        print(f"文件 {input_path} 不存在")
        return
    
    # 更新输入路径为绝对路径
    args.input = input_path
    
    # 确保输出目录存在
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, args.output)
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 更新输出路径为绝对路径
    args.output = output_path
    
    print(f"读取文件 {args.input}...")
    df = read_file(args.input)
    
    print("分析数据...")
    analysis_df = analyze_manu_enterprise_brand(df)
    
    print(f"输出分析结果文件 {args.output}...")
    analysis_df.to_csv(args.output, index=False)
    
    # 统计结果
    print("\n=== 分析结果统计 ===")
    
    # 类型分布
    type_distribution = analysis_df['type_case'].value_counts()
    print("\n类型分布:")
    for type_case, count in type_distribution.items():
        print(f"{type_case}: {count} 个manu_no")
    
    # 状态分布
    status_distribution = analysis_df['status'].value_counts()
    print("\n状态分布:")
    for status, count in status_distribution.items():
        print(f"{status}: {count} 个manu_no")
    
    # 可填充统计
    fillable_a1 = analysis_df[(analysis_df['type_case'] == 'A1') & (analysis_df['confidence'] >= 0.7)]
    fillable_b = analysis_df[(analysis_df['type_case'] == 'B') & (analysis_df['confidence'] >= 0.6)]
    
    total_fillable_ents = fillable_a1['empty_ent'].sum() + fillable_b['empty_ent'].sum()
    total_fillable_brands = fillable_a1['empty_brand'].sum()
    
    print("\n可填充统计:")
    print(f"A1可填充manu_no数量: {len(fillable_a1)}")
    print(f"B可填充manu_no数量: {len(fillable_b)}")
    print(f"可填充enterprise记录数: {total_fillable_ents}")
    print(f"可填充brand记录数: {total_fillable_brands}")
    
    print("\n分析完成！")

if __name__ == "__main__":
    main()
