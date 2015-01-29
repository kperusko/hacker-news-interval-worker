import json
import requests
from models import JSONSerializable

class HTTPService(object):
    BASE_URL = ""
    FORMAT = ""

    def build_url(self, resource, resource_id=""):
        url = self.BASE_URL + resource
        if resource_id != "":
            url = url + "/"

        url = url + resource_id + self.FORMAT
        return url

    def exec_request(self, verb, resource, resource_id="", data=None):
        url = self.build_url(resource, resource_id)
        headers = {"content-type": "application/json"}

        allowed_actions = {"get": requests.get, "post": requests.post,
                           "put": requests.put, "patch": requests.patch}

        if verb not in allowed_actions:
            raise ValueError("Action %s is not allowed " % verb)

        try:
            if not data:
                response = allowed_actions[verb](url)
            else:
                response = allowed_actions[verb](url=url, data=data, headers=headers)

            if response.status_code != requests.codes.ok and \
               response.status_code != requests.codes.created:
                print "Action %s failed for url %s with code %s" % (verb, url, response.status_code)
                return None

            return response.json()

        except requests.exceptions.RequestException, e: 
            print "Request exception %s occured" % e.code
            

    def get(self, resource, resource_id=""):
        return self.exec_request("get", resource, resource_id)

    def post(self, resource, data):
        data = data.to_json()
        return self.exec_request(verb="post", resource=resource, data=data)

    def put(self, resource, resource_id, data):
        data = data.to_json()
        return self.exec_request("put", resource, resource_id, data)

    def patch(self, resource, resource_id, data):
        data = json.dumps(data, default=JSONSerializable.json_encode)
        return self.exec_request("patch", resource, resource_id, data)


class HackerNewsInterval(HTTPService):
    BASE_URL = ""
    STORY_IDS_URL = "story/ids"
    STORY_URL = "story"
    SNAPSHOTS_URL = "snapshots"
    SNAPSHOT_URL = "snapshot"

    def __init__(self, base_url):
        self.BASE_URL = base_url

    def get_story_ids(self):
        return self.get(self.STORY_IDS_URL)

    def add_story(self, story):
        return self.put(self.STORY_URL, str(story._id), story)

    def update_story(self, story_id, score):
        update = {"op": "add", "path": "scores", "value": score}
        return self.patch(self.STORY_URL, str(story_id), update)

    def create_snapshot(self, snapshot):
        return self.post(self.SNAPSHOTS_URL, snapshot)

    def update_snapshot(self, snapshot):
        return self.put(self.SNAPSHOT_URL, str(snapshot._id), snapshot)


class HackerNews(HTTPService):
    BASE_URL = "https://hacker-news.firebaseio.com/v0/"
    FORMAT = ".json"
    TOP_STORY_URL = "topstories"
    TOP_STORY_LIMIT = 100  # number of ids returned from HN API
    ITEM_URL = "item"
    FORMAT = ".json"

    def get_top_stories(self, limit=100):
        # limit the max number of stories we can fetch
        if 0 > limit > HackerNews.TOP_STORY_LIMIT:
            limit = 100

        response = self.get(self.TOP_STORY_URL)

        if response is None:
            return []
        else:
            return response[:limit]

    def get_story(self, story_id):
        return self.get(self.ITEM_URL, str(story_id))
