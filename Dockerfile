# 使用拉取的 Python 基础镜像
FROM python:3.7
quent_sanderson

# 设置工作目录
WORKDIR /app

# 复制当前目录的内容到工作目录
COPY . /app

# 安装必要的依赖库
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0

# 安装 PaddleOCR 的依赖并使用清华源
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 PaddleOCR 及其依赖并使用清华源
RUN pip install paddlepaddle paddleocr -i https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 TensorFlow 和其他依赖并使用清华源
RUN pip install tensorflow==2.4.1 absl-py==0.10 flatbuffers==1.12 gast==0.3.3 grpcio==1.32.0 numpy==1.19.2 six==1.15.0 tensorflow-estimator==2.4.0 termcolor==1.1.0 typing-extensions==3.7.4 wrapt==1.12.1 -i https://pypi.tuna.tsinghua.edu.cn/simple

# 运行你的 Python 脚本
CMD ["python", "wenzishibie.py"]

