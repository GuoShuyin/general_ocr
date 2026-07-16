# 中文文档 OCR API

[English](./README.md)

这是一个基于 Flask 的 OCR 服务，用于从中文商业与身份证件文档中提取结构化信息。项目结合 PaddleOCR、OpenCV 图像预处理和面向不同文档类型的解析规则，并通过 HTTP API 提供识别能力。

## 我完成的工作

- 构建接收图片和 PDF，并返回结构化 OCR 结果的 Flask API。
- 实现图像旋转与方向矫正等预处理流程。
- 实现发票、中国身份证、银行卡和车牌的文档特定字段提取。
- 为下游系统提供英文 API 字段名，同时保留中文文档支持。
- 实现表格转 Excel、文档转 DOCX 的工作流。
- 为原始项目环境提供 Docker 部署配置。

## 支持的工作流

| 输入 | 输出 |
| --- | --- |
| 中文发票、身份证、银行卡和车牌 | 结构化 JSON 字段 |
| 图片和 PDF | OCR 文本与提取后的文档数据 |
| 表格 | Excel 工作簿 |
| 文档 | 重建后的 DOCX 文件 |

## API 概览

服务入口为 [`general_API_service.py`](./general_API_service.py)，提供 `POST /ocr` 接口，接收文件和文档类型参数。

```bash
curl -X POST "http://localhost:5000/ocr?type=invoice" \
  -F "file=@sample_invoice.png"
```

可用文档类型包括：`invoice`、`id_card`、`bank_card`、`license_plate`、`excel` 和 `document`。

> 请不要在公开演示中使用真实身份证、银行卡或发票。请只使用合成数据或已完全脱敏的样例。

## 仓库说明

- [`general_API_service.py`](./general_API_service.py)：Flask 路由与请求处理。
- [`general_ocr_API.py`](./general_ocr_API.py)：OCR 编排与面向不同文档的字段提取。
- [`general_ocr.py`](./general_ocr.py)：原始 OCR 实现与预处理工具。
- [`generalOCR接口使用文档.pdf`](./generalOCR接口使用文档.pdf)：中文 API 接口说明。
- [`通用识别使用开发文档.pdf`](./通用识别使用开发文档.pdf)：中文开发文档。

该项目服务于中文文档工作流，因此保留了中文 PDF 文档；英文 README 用于帮助国际招聘方和协作者快速了解项目。

## 本地环境

该项目为归档项目，原始环境使用 Python 3.7。运行 API 前，请安装 Python 依赖和 `pdf2image` 所需的 Poppler 系统包：

```bash
python -m pip install -r requirements.txt
# macOS：brew install poppler
# Ubuntu/Debian：sudo apt-get install poppler-utils
```

仓库中的推理资源和部署脚本保留了原始项目环境。若要将其作为生产可运行包使用，建议先完成干净环境的 smoke test 和 Docker 配置更新。

## 第三方依赖与说明

本项目使用 [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) 及其相关推理资源完成 OCR。PaddleOCR 及任何复制的上游组件仍受其原始作者的许可证约束；详细说明见 [`NOTICE.md`](./NOTICE.md)。仓库中的 Flask API、图像预处理和文档特定字段提取流程为 Shuyin Guo 的项目工作。
