import datetime
import json

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
