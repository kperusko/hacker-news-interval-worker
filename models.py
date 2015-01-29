"""
Data structures that mirror models in Hacker News Interval app
"""

import datetime
import json

class JSONSerializable(object):
    """
    Abstract class that's not to be instantiated.
    It's purpose is to provide custom serialization
    functionality  for all models
    """
    @staticmethod
    def json_encode(obj):
        """
        Serialize the provided obj into JSON
        """
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif obj is None:
            return
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            raise TypeError("Object of type %s is not JSON serializable" % type(obj))

    def to_json(self):
        """Serialize object to JSON formatted string"""
        return json.dumps(self, default=self.json_encode)


class Snapshot(JSONSerializable):
    """
    Represents a point in time when the data is collected
    from the Hacker News API and stored to Hacker News Interval app
    """
    def __init__(self, snapshot=None):
        self._id = None
        self.time = datetime.datetime.utcnow()
        self.new_items = 0

        if snapshot:
            self._id = snapshot["_id"]
            self.time = snapshot["time"]
            self.new_items = snapshot["new_items"]


class Story(JSONSerializable):
    """
    Represents a single item
    that is collected from the Hacker News
    """
    ITEM_URL = "https://news.ycombinator.com/item?id="

    def __init__(self):
        self._id = 0
        self.title = ""
        self.by = ""
        self.created = datetime.datetime.now()
        self.scores = []  # list of Score objects
        self.url = self.ITEM_URL + str(self._id)


class Score(JSONSerializable):
    """
    Represents a score and rank that story had
    when the snapshot was taken.
    Score objects are stored in Story object.
    """
    def __init__(self, score, rank, snapshot_id):
        self.score = score
        self.rank = rank
        self.snapshot = snapshot_id
