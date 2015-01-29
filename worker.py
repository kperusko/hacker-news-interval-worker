
#!/usr/bin/env python

"""
Hacker News Interval worker
Background worker that collects that from the
official HackerNews Firebase API and stores it
to the Hacker News Interval application
"""

import sys
import datetime
import config
from services import HackerNewsInterval, HackerNews
from models import Snapshot, Story, Score


class StoryCollector(object):
    """
    Collects stories from the Hacker News API
    and saving them on the Hacker News Interval
    """
    def __init__(self, hacker_news_service, news_interval_service):
        self.__stories = None
        self.__stories_to_update = None
        self.__stories_to_add = None
        self.__hn = hacker_news_service
        self.__ni = news_interval_service

    def collect(self):
        """
        Collect top IDs from HN and compare them to existing ones from
        HN Interval
        """
        top_story_ids = self.__stories = self.__hn.get_top_stories()

        if top_story_ids is None:
            print "Couldn't load top stories from HN"
            sys.exit(1)

        existing_story_ids = self.__ni.get_story_ids()

        if existing_story_ids is None:
            print "Couldn't load existing story ids"
            sys.exit(1)

        top_story_ids = set(top_story_ids)
        existing_story_ids = set(existing_story_ids)
        self.__stories_to_update = set.intersection(top_story_ids,
                                                    existing_story_ids)
        self.__stories_to_add = top_story_ids - existing_story_ids

    def save(self):
        """
        Save new stories and add new scores for existing ones
        """
        # Create a new snapshot
        snapshot_json = self.__ni.create_snapshot(Snapshot())
        if snapshot_json is None:
            print "Couldn't create new snapshot"
            sys.exit(1)

        snapshot = Snapshot(snapshot_json)

        story_num = int(config.app["story_number"])
        skipped = added = updated = 0

        for rank, story_id in enumerate(self.__stories):
            # Rank of the story is position in the array
            # If we skipped adding a story, adjust the rank
            # so we don't have inconsistent ranks
            rank = rank + 1 - skipped
            # Get story from HN and create a Story object
            story = create_story(self.__hn.get_story(story_id),
                                 rank, snapshot)

            # Skip it if we can't create a story from HN response
            # Happens when we have comment in top ids
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

        # Update snapshot data
        snapshot.new_items = added
        self.__ni.update_snapshot(snapshot)

        print "Added stories: " + str(added)
        print "Updated stories: " + str(updated)
        print "Skipped stories: " + str(skipped)

def create_story(story_json, rank, snapshot):
    """
    Create a Story model from JSON encoded content
    """

    # Check if data contains all required fields
    required_fields = ("id", "title", "by", "time", "score")
    if not all(k in story_json for k in required_fields):
        return None

    story = Story()
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
    """
    Collect data from HN and save it to HN Interval
    """
    print "======================================================="
    print "Started collecting stories: " + datetime.datetime.now().isoformat()
    story_collector = StoryCollector(
        HackerNews(config.app["hn_url"]),
        HackerNewsInterval(config.app["interval_url"]))
    story_collector.collect()
    story_collector.save()
    print "Ended collecting stories: " + datetime.datetime.now().isoformat()
    print ""


if __name__ == "__main__":
    collect_data()
