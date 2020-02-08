import requests
import re
from fake_useragent import UserAgent
import time

ua = UserAgent()

headers = {"user-agent": ua.random}


class UserMoviesUrl(object):
    base_url = "https://movie.douban.com/people/%(user_id)s/%(type)s"

    def __init__(self, user_id):
        self.user_id = user_id

    def get_index_url(self):
        """返回用户电影主页url
        例如:https://movie.douban.com/people/zhouxiaopo/
        """
        return self.base_url % {"user_id": str(self.user_id), "type": ""}

    def get_wish_url(self):
        """用户想看的电影 url"""
        return self.base_url % {"user_id": str(self.user_id), "type": "wish"}

    def get_do_url(self):
        """用户在看的电视剧 url"""
        return self.base_url % {"user_id": str(self.user_id), "type": "do"}

    def get_collect_url(self):
        """用户看过的电影 url"""
        return self.base_url % {"user_id": str(self.user_id), "type": "collect"}


def get_response_text_by_url(url):
    """返回指定url的字符类型响应"""
    time.sleep(10)  # 请求一次 休息5' 避免爬虫被ban
    response = requests.get(url=url, headers=headers)
    content = response.text
    return content


def get_movies_id_one_page(movie_url):
    """返回当前页面的所有电影的唯一 id
    """
    content = get_response_text_by_url(movie_url)
    # 编译正则表达式
    re_str = "https\:\/\/movie\.douban\.com\/subject\/([0-9]+)\/"
    re_compiled = re.compile(re_str)
    object_list = re_compiled.findall(content)
    # 去重复
    return list(set(object_list))


def get_movies_count(current_user):
    """ 返回用户看过，想看 ，在看的电影（电视剧数量）
    type(current_user)=UserMoviesUrl
    """
    index_content = get_response_text_by_url(current_user.get_index_url())
    re_str = 'target\="\_self"\>([0-9]+)部'
    re_compiled = re.compile(re_str)
    # 返回长度为3的列表 分别表示 ‘看过‘，’想看‘，’在看‘
    result_list = re_compiled.findall(index_content)
    assert len(result_list) == 3

    return result_list


def get_all_page_movie_id(first_url, count):
    """获取所有页面的movie id
    first_url: 第一页url
    count : 总个数
    return type: list
    """
    first_url = first_url + "?start=%s"
    movies_id = []
    for i in range(0, int(count), 15):
        movies_id += get_movies_id_one_page(first_url % str(i))
    return movies_id


def get_user_profile_movies(user_id=None):
    """
    返回三个列表，分别包含看过，想看,  在看的电影id
    """
    if not user_id:
        return [], [], []
    current_user = UserMoviesUrl(user_id)

    count_list = get_movies_count(current_user)
    collect_movies_count = count_list[0]
    wish_movies_count = count_list[1]
    do_movies_count = count_list[2]

    collect_movies = get_all_page_movie_id(
        current_user.get_collect_url(), collect_movies_count
    )
    wish_movies = get_all_page_movie_id(current_user.get_wish_url(), wish_movies_count)
    do_movies = get_all_page_movie_id(current_user.get_do_url(), do_movies_count)

    # assert len(collect_movies)==collect_movies_count
    # assert len(wish_movies)==wish_movies_count
    # assert len(do_movies)==do_movies_count

    return collect_movies, wish_movies, do_movies
