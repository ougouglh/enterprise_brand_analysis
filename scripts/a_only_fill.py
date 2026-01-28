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
    
    # 去首尾空格
    text = text.strip()
    
    # 处理空值占位符
    null_placeholders = ['-', 'NULL', 'N/A', '无此条码', '无法识别', '物品']
    if text in null_placeholders:
        return ''
    
    # 全半角统一
    text = text.replace('，', ',').replace('。', '.').replace('；', ';').replace('：', ':')
    text = text.replace('（', '(').replace('）', ')').replace('【', '[').replace('】', ']')
    
    # 大小写统一（英文）
    # text = text.lower()  # 暂时注释，避免影响品牌名大小写
    
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

# 分析A桶
def analyze_a_buckets(df):
    # 预处理
    df['normalized_enterprise'] = df['enterprise'].apply(normalize_text)
    df['normalized_brand'] = df['brand'].apply(normalize_text)
    
    # 拆分多值
    df['enterprise_tokens'] = df['normalized_enterprise'].apply(split_values)
    df['brand_tokens'] = df['normalized_brand'].apply(split_values)
    
    # 按manu_no分组分析
    groups = df.groupby('manu_no')
    a_buckets = []
    enterprise_fill_list = []
    brand_fill_list = []
    
    for manu_no, group in groups:
        # 收集所有非空的enterprise和brand
        all_enterprises = []
        all_brands = []
        
        for tokens in group['enterprise_tokens']:
            all_enterprises.extend(tokens)
        
        for tokens in group['brand_tokens']:
            all_brands.extend(tokens)
        
        # 过滤空值
        all_enterprises = [e for e in all_enterprises if e != '']
        all_brands = [b for b in all_brands if b != '']
        
        # 计算唯一性
        enterprise_unique = len(set(all_enterprises))
        brand_unique = len(set(all_brands))
        
        # 检查是否为A桶
        is_a_bucket = (enterprise_unique == 1) and (brand_unique == 1)
        
        if is_a_bucket:
            # 获取唯一值
            enterprise_fill_value = list(set(all_enterprises))[0] if all_enterprises else ''
            brand_fill_value = list(set(all_brands))[0] if all_brands else ''
            
            # 计算支持数
            support_cnt_ent = len(all_enterprises)
            support_cnt_brand = len(all_brands)
            total_rows = len(group)
            support_ratio_ent = support_cnt_ent / total_rows if total_rows > 0 else 0
            support_ratio_brand = support_cnt_brand / total_rows if total_rows > 0 else 0
            
            # 质量闸门
            quality_check = (support_cnt_ent >= 1) and (support_cnt_brand >= 1)
            
            if quality_check:
                # 生成填充清单
                for idx, row in group.iterrows():
                    # enterprise填充
                    if row['normalized_enterprise'] == '':
                        enterprise_fill_list.append({
                            'manu_no': manu_no,
                            'row_id': row['id'],
                            'old_enterprise': row['enterprise'],
                            'new_enterprise': enterprise_fill_value,
                            'status': 'A_OK_FILL',
                            'support_cnt_ent': support_cnt_ent,
                            'support_cnt_brand': support_cnt_brand,
                            'total_rows_in_manu_no': total_rows,
                            'support_ratio_ent': support_ratio_ent,
                            'support_ratio_brand': support_ratio_brand
                        })
                    
                    # brand填充
                    if row['normalized_brand'] == '':
                        brand_fill_list.append({
                            'manu_no': manu_no,
                            'row_id': row['id'],
                            'old_brand': row['brand'],
                            'new_brand': brand_fill_value,
                            'status': 'A_OK_FILL',
                            'support_cnt_ent': support_cnt_ent,
                            'support_cnt_brand': support_cnt_brand,
                            'total_rows_in_manu_no': total_rows,
                            'support_ratio_ent': support_ratio_ent,
                            'support_ratio_brand': support_ratio_brand
                        })
                
                # 记录A桶信息
                a_buckets.append({
                    'manu_no': manu_no,
                    'manu_name': group['manu_name'].iloc[0] if not group.empty else '',
                    'total_rows': total_rows,
                    'support_cnt_ent': support_cnt_ent,
                    'support_cnt_brand': support_cnt_brand,
                    'enterprise_fill_value': enterprise_fill_value,
                    'brand_fill_value': brand_fill_value,
                    'support_ratio_ent': support_ratio_ent,
                    'support_ratio_brand': support_ratio_brand
                })
    
    return pd.DataFrame(a_buckets), pd.DataFrame(enterprise_fill_list), pd.DataFrame(brand_fill_list)

# 主函数
def main():
    parser = argparse.ArgumentParser(description='A桶填充分析')
    parser.add_argument('--input', default='../data/ner_key_product_info_top95.csv', help='输入文件路径')
    parser.add_argument('--output_dir', default='../output', help='输出目录')
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
    # 使用基于脚本位置的绝对路径
    output_path = os.path.join(script_dir, args.output_dir)
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)
    
    # 更新输出目录为绝对路径
    args.output_dir = output_path
    
    print(f"读取文件 {args.input}...")
    df = read_file(args.input)
    
    print("分析A桶...")
    a_buckets, enterprise_fill_list, brand_fill_list = analyze_a_buckets(df)
    
    # 输出结果
    a_buckets_output = os.path.join(args.output_dir, 'a_buckets_analysis.csv')
    enterprise_fill_output = os.path.join(args.output_dir, 'enterprise_fill_list.csv')
    brand_fill_output = os.path.join(args.output_dir, 'brand_fill_list.csv')
    
    a_buckets.to_csv(a_buckets_output, index=False)
    enterprise_fill_list.to_csv(enterprise_fill_output, index=False)
    brand_fill_list.to_csv(brand_fill_output, index=False)
    
    # 统计结果
    print(f"\n=== 分析结果 ===")
    print(f"A桶数量: {len(a_buckets)}")
    print(f"可填充enterprise记录数: {len(enterprise_fill_list)}")
    print(f"可填充brand记录数: {len(brand_fill_list)}")
    print(f"总可填充记录数: {len(enterprise_fill_list) + len(brand_fill_list)}")
    
    print(f"\n输出文件:")
    print(f"A桶分析: {a_buckets_output}")
    print(f"Enterprise填充清单: {enterprise_fill_output}")
    print(f"Brand填充清单: {brand_fill_output}")

if __name__ == "__main__":
    main()
