"""
Services for communicating with Hacker News REST API
and Hacker News Interval REST API
"""

import json
import requests
from models import JSONSerializable

class HTTPService(object):
    """
    Abstract class service that implements common methods for
    all HTTP services
    """
    # Base url for the service
    # example: http://example.com/api/
    BASE_URL = ""
    # Format suffix (.json) - optional
    FORMAT = ""

    def build_url(self, resource, resource_id=""):
        """
        Create url in the following format
        BASE_URL/resource/resource_id.FORMAT
        """
        url = self.BASE_URL + resource
        if resource_id != "":
            url = url + "/"

        url = url + resource_id + self.FORMAT
        return url

    def exec_request(self, request, resource, resource_id="", data=None):
        """
        Execute HTTP request
        """
        url = self.build_url(resource, resource_id)
        headers = {"content-type": "application/json"}

        # Limit actions we're allowing
        allowed_actions = {"get": requests.get, "post": requests.post,
                           "put": requests.put, "patch": requests.patch}

        if request not in allowed_actions:
            raise ValueError("Action %s is not allowed " % request)

        # Execute HTTP request provided by request
        try:
            if not data:
                response = allowed_actions[request](url)
            else:
                response = allowed_actions[request](url=url, data=data, headers=headers)

            if response.status_code != requests.codes.ok and \
               response.status_code != requests.codes.created:
                print "Action %s failed for url %s with code %s" % \
                    (request, url, response.status_code)
                return None

            return response.json()
        except requests.exceptions.RequestException, e:
            print "Request exception occured "
            print "Action %s failed for url %s" % (request, url)
            print e
            return None


    def get(self, resource, resource_id=""):
        """Execute HTTP GET request to a given resource"""
        return self.exec_request("get", resource, resource_id)

    def post(self, resource, data):
        """
        Execute HTTP POST request to a given resource
        with given data
        """
        data = data.to_json()
        return self.exec_request(request="post", resource=resource, data=data)

    def put(self, resource, resource_id, data):
        """
        Execute HTTP PUT request to a given resource
        with given data
        """
        data = data.to_json()
        return self.exec_request("put", resource, resource_id, data)

    def patch(self, resource, resource_id, data):
        """
        Execute HTTP PATCH request to a given resource
        with given data
        """
        data = json.dumps(data, default=JSONSerializable.json_encode)
        return self.exec_request("patch", resource, resource_id, data)


class HackerNewsInterval(HTTPService):
    """
    Service that interacts with Hacker News Interval REST API
    """
    BASE_URL = ""  # URL of the service
    STORY_IDS_URL = "story/ids"  # route for getting existing story ids
    STORY_URL = "story"  # route for creating/updating stories
    SNAPSHOTS_URL = "snapshots"  # route for creating snapshots
    SNAPSHOT_URL = "snapshot"  # route for updating snapshots

    def __init__(self, base_url):
        self.BASE_URL = base_url

    def get_story_ids(self):
        """Get all story IDs that exist on HN interval"""
        return self.get(self.STORY_IDS_URL)

    def add_story(self, story):
        """Create new story on HN interval"""
        return self.put(self.STORY_URL, str(story._id), story)

    def update_story(self, story_id, score):
        """Add new score to the existing story"""

        # Create a valid PATCH for updating scores
        update = {"op": "add", "path": "scores", "value": score}
        return self.patch(self.STORY_URL, str(story_id), update)

    def create_snapshot(self, snapshot):
        """Create new snapshot on HN interval"""
        return self.post(self.SNAPSHOTS_URL, snapshot)

    def update_snapshot(self, snapshot):
        """Update snapshot with data"""
        return self.put(self.SNAPSHOT_URL, str(snapshot._id), snapshot)


class HackerNews(HTTPService):
    """
    Service that interacts with Hacker News API
    """
    BASE_URL = ""
    FORMAT = ".json"
    TOP_STORY_URL = "topstories"
    TOP_STORY_LIMIT = 100  # number of ids returned from HN API
    ITEM_URL = "item"
    FORMAT = ".json"


    def __init__(self, base_url):
        self.BASE_URL = base_url

    def get_top_stories(self, limit=100):
        """Get top story IDs from HN"""
        # limit the max number of stories we can fetch
        if 0 > limit > HackerNews.TOP_STORY_LIMIT:
            limit = 100

        response = self.get(self.TOP_STORY_URL)

        if response is None:
            return None
        else:
            return response[:limit]

    def get_story(self, story_id):
        """Get the story for provided ID"""
        return self.get(self.ITEM_URL, str(story_id))
