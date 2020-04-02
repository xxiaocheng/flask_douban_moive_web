# 使用Flask 实现的电影评分网站
## [在线地址](http://www.todayx.xyz)

### 项目总体使用前后端分离技术，后端使用Flask 开发RESTful api ，前端使用vue进行开发，这是项目的后端部分，前端代码[请移步](https://github.com/xxiaocheng/douban_movie_vue_front_end)


## Getting Started

### 必需
- [python3](https://www.python.org/)
- [pipenv](https://github.com/pypa/pipenv)
- [Redis](https://redis.io/)
- [MySQL](https://www.mysql.com/)
- [Elasticsearch](https://www.elastic.co/cn/elasticsearch)

### 安装依赖
#### 开发环境
```
pipenv install --dev
```
#### 生产环境
```
pipenv install
```
### 初始化数据
```
flask db init
```
### 运行
```
flask run
```
### 启动 celery
```
celery worker -A celery_worker.celery -B --loglevel=info
```

## 如有问题请联系 cxxlxx0@gmail.com
