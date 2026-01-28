# Enterprise Brand Analysis

企业品牌数据分析工具，用于分析产品数据中的品牌信息完整性。

## 项目简介

本项目提供了一套工具，用于分析和统计产品数据中的品牌信息，帮助企业了解品牌数据的完整性和质量。

## 功能特点

- **品牌信息完整性分析**：按厂商编号分组，分析品牌信息的完整性
- **多维度统计**：提供多种场景的统计结果，全面了解数据质量
- **详细记录导出**：支持导出各场景的详细记录，便于进一步分析
- **数据清洗**：自动处理空值和占位符，提高数据质量

## 文件说明

### 脚本文件

- `scripts/fenxi.py` - 品牌分析主脚本
  - 按 `manu_no` 分组统计品牌信息
  - 生成四种场景的统计结果
  - 支持导出详细记录
  
- `scripts/enhanced_analysis.py` - 增强分析脚本
  - 提供更深入的数据分析功能
  - 生成额外的统计维度

- `scripts/a_only_fill.py` - 数据填充脚本
  - 用于处理和填充缺失的品牌信息
  - 辅助数据质量改进

### 配置文件

- `.gitignore` - Git忽略配置，排除CSV文件和输出目录

## 使用方法

### 基本使用

```bash
# 使用默认配置运行（输入文件为 data.csv，输出到 out 目录）
python scripts/fenxi.py

# 指定输入文件和输出目录
python scripts/fenxi.py --input data.csv --output_dir out

# 导出详细记录
python scripts/fenxi.py --export_details
```

### 参数说明

- `--input`：输入CSV文件路径（默认：data.csv）
- `--output_dir`：输出目录（默认：out）
- `--encoding`：CSV文件编码（默认：utf-8）
- `--sep`：CSV分隔符（默认：,）
- `--export_details`：导出每个场景的详细记录

## 统计场景

### 场景1：enterprise 和 brand 唯一但有记录为空
同一 `manu_no` 下，`enterprise` 和 `brand` 都有唯一且存在的值，但仍有记录的 `enterprise` 或 `brand` 为空。

### 场景2：enterprise 唯一、brand 多种但有记录为空
同一 `manu_no` 下，`enterprise` 有唯一且存在的值，`brand` 有多种不同值，但仍有记录的 `enterprise` 或 `brand` 为空。

### 场景3：enterprise 和 brand 全空但有备选品牌
同一 `manu_no` 下，`enterprise` 和 `brand` 都为空，但 `mt_brand_name` 或 `eb_brand_name` 至少有一个存在。

### 场景4：完全无品牌信息
同一 `manu_no` 下，所有品牌相关字段都为空。

## 输出结果

### summary.csv
包含各场景的汇总统计：
- `case`：场景名称
- `row_count`：符合该场景的记录条数
- `manu_no_count`：符合该场景的 manu_no 数量

### 详细记录文件
当使用 `--export_details` 参数时生成：
- `case1_details.csv`：场景1的详细记录
- `case2_details.csv`：场景2的详细记录
- `case3_details.csv`：场景3的详细记录
- `case4_details.csv`：场景4的详细记录

## 数据要求

输入CSV文件需要包含以下字段：
- `manu_no`：厂商编号（必需）
- `enterprise`：企业名称
- `brand`：品牌名称
- `mt_brand_name`：美团品牌名称
- `eb_brand_name`：饿了么品牌名称

## 数据清洗

脚本会自动处理以下占位符，将其转换为空值：
- 空字符串 ""
- 单个空格 " " 和双空格 "  "
- "无此条码"
- "无法识别"
- "搜条码"
- "NULL", "null", "None", "none", "N/A", "n/a"

## 注意事项

1. 确保输入CSV文件编码正确（默认utf-8）
2. 输出目录会自动创建，无需手动创建
3. 对于大型数据集，建议使用足够内存的运行环境
4. CSV文件不会被上传到Git仓库，请在本地妥善保管

## 依赖要求

- Python 3.7+
- pandas
- argparse

安装依赖：
```bash
pip install pandas argparse
```

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题或建议，欢迎通过GitHub Issues反馈。
