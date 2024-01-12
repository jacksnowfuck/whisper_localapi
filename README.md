# whisper_localapi
whisper本地离线模型以openai的api模式侦听，含客户端实时录音转文字

## server.py
在服务器运行，会自动从huggingface下载模型

## client.py
在客户端运行，运行后不断侦听本地的麦克风，距离近识别效果很优秀，隔远了会差很多