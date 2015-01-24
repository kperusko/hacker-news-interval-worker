import datetime
import json
import requests
import config

class JSONSerializable(object):
    @staticmethod
    def json_encode(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif obj is None:
            return
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            raise TypeError("Object of type %s is not JSON serializable" % type(obj))

    def to_json(self):
        return json.dumps(self, default=self.json_encode)


class Score(JSONSerializable):
    def __init__(self, score, rank, snapshot_id):
        self.score = score
        self.rank = rank
        self.snapshot = snapshot_id


class Story(JSONSerializable):
    ITEM_URL = "https://news.ycombinator.com/item?id="

    def __init__(self):
        self._id = 0
        self.title = ""
        self.by = ""
        self.created = datetime.datetime.now()
        self.scores = []
        self.url = self.ITEM_URL + str(self._id)


class Snapshot(JSONSerializable):
    def __init__(self, snapshot=None):
        self._id = None
        self.time = datetime.datetime.utcnow()
        self.new_items = 0

        if snapshot:
            self._id = snapshot["_id"]
            self.time = snapshot["time"]
            self.new_items = snapshot["new_items"]


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

        if not data:
            return allowed_actions[verb](url)
        else:
            return allowed_actions[verb](url=url, data=data, headers=headers)

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
    BASE_URL = config.app["interval_url"]
    STORY_IDS_URL = "story/ids"
    STORY_URL = "story"
    SNAPSHOTS_URL = "snapshots"
    SNAPSHOT_URL = "snapshot"

    def get_story_ids(self):
        response = self.get(self.STORY_IDS_URL)

        if response.status_code != requests.codes.ok:
            return []

        return response.json()

    def add_story(self, story):
        return self.put(self.STORY_URL, str(story._id), story)

    def update_story(self, story_id, score):
        update = {"op": "add", "path": "scores", "value": score}
        return self.patch(self.STORY_URL, str(story_id), update)

    def create_snapshot(self, snapshot):
        response = self.post(self.SNAPSHOTS_URL, snapshot)

        if response.status_code == requests.codes.ok:
            return response.json()

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

        if response.status_code != requests.codes.ok:
            return []

        return response.json()[:limit]

    def get_story(self, story_id):
        response = self.get(self.ITEM_URL, str(story_id))

        if response.status_code != requests.codes.ok:
            return {}

        return response.json()


class StoryCollector(object):
    def __init__(self, hacker_news_service, news_interval_service):
        self.__stories_to_update = None
        self.__stories_to_add = None
        self.__hn = hacker_news_service
        self.__ni = news_interval_service

    def collect(self):
        top_story_ids = self.__hn.get_top_stories()
        existing_story_ids = self.__ni.get_story_ids()

        # create a dictionary where key is id of the story
        # and value is a rank (index of the item in array)
        self.__stories = {v: k+1 for k, v in enumerate(top_story_ids)}

        top_story_ids = set(top_story_ids)
        existing_story_ids = set(existing_story_ids)
        self.__stories_to_update = set.intersection(top_story_ids,
                                                    existing_story_ids)
        self.__stories_to_add = top_story_ids - existing_story_ids

    def save(self):
        snapshot_json = self.__ni.create_snapshot(Snapshot())
        snapshot = Snapshot(snapshot_json)

        story_num = int(config.app["story_number"])
        skipped = added = updated = 0
        for story_id, rank in self.__stories.iteritems():
            rank = self.__stories[story_id] - skipped
            story = self.createStory(self.__hn.get_story(story_id), rank, snapshot)

            if not story: 
                skipped += 1
                continue
            if story_id in self.__stories_to_add:
                added += 1
                self.__ni.add_story(story)
            else: 
                updated += 1
                self.__ni.update_story(story_id, story.scores[0])

            story_num -= 1
            if story_num <= 0:
                break          


        snapshot.new_items = added
        self.__ni.update_snapshot(snapshot)

        print "Added stories: " + str(added)
        print "Updated stories: " + str(updated)
        print "Skipped stories: " + str(skipped)

    def createStory(self, story_json, rank, snapshot):
        story = Story()
        required_fields = ("id", "title", "by", "time", "score")

        if not all (k in story_json for k in required_fields):
            return None

        story._id = story_json["id"]
        story.title = story_json["title"]
        story.by = story_json["by"]
        story.created = datetime.datetime.fromtimestamp(story_json["time"])
        story.scores = [Score(story_json["score"], rank, snapshot._id)]
        # job story type doesn't have url
        # so we need to create a link to story on the HN
        story.url = story_json["url"] or Story.ITEM_URL + str(story_json["id"])
        return story
        

def collect_data():
    sc = StoryCollector(HackerNews(), HackerNewsInterval())
    sc.collect()
    sc.save()

if __name__ == "__main__":
    collect_data()
