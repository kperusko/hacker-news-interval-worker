# Hacker News Interval Worker
Worker service that collects data from the official Hacker News API and saves them to the [Hacker News Interval app](https://github.com/kperusko/hacker-news-interval).

# Usage

The file [worker.py](../master/worker.py) is intended to started from a cronjob. 

Example crontab entry that is started every hour:
```bash
0 * * * * /usr/bin/python /worker/worker.py >> /worker/worker.log
```
