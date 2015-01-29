
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
    def __init__(self, hacker_news_service, news_interval_service):
        self.__stories = None
        self.__stories_to_update = None
        self.__stories_to_add = None
        self.__hn = hacker_news_service
        self.__ni = news_interval_service

    def collect(self):
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
        snapshot_json = self.__ni.create_snapshot(Snapshot())
        snapshot = Snapshot(snapshot_json)

        story_num = int(config.app["story_number"])
        skipped = added = updated = 0

        for rank, story_id in enumerate(self.__stories):
            rank = rank + 1 - skipped
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
    print "======================================================="
    print "Started collecting stories: " + datetime.datetime.now().isoformat()
    sc = StoryCollector(HackerNews(), HackerNewsInterval(config.app["interval_url"]))
    sc.collect()
    sc.save()
    print "Ended collecting stories: " + datetime.datetime.now().isoformat()
    print ""


if __name__ == "__main__":
    collect_data()
