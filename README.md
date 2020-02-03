# 使用Flask 实现的电影评分网站
## [在线地址](http://www.todayx.xyz)

### 项目总体使用前后端分离技术，后端使用Flask 开发RESTful api ，前端使用vue进行开发，这是项目的后端部分，前端代码[请移步](https://github.com/xxiaocheng/douban_movie_vue_front_end)


## Getting Started

### 必需
- [python3](https://www.python.org/)
- [pipenv](https://github.com/pypa/pipenv)
- [Redis](https://redis.io/)
- [MongoDB](https://www.mongodb.com/download-center)
- elasticsearch
```
docker run -d -p 9200:9200 --name elasticsearch -p 9300:9300 -v /home/xiao/Coding/dockerV/elasticsearch:/usr/share/elasticsearch/data -e "discovery.type=single-node" docker.elastic.co/elasticsearch/elasticsearch:7.5.2
```
### 安装依赖
#### 开发环境
```
pipenv install --dev
```
#### 生产环境
```
pipenv install 
```

### 运行
```
flask run 
```
### start celery worker
```
celery worker -A celery_worker.celery --loglevel=info
```

## 如有问题请联系 cxxlxx0@gmail.com
