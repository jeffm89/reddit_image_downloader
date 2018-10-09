# reddit_image_downloader

**Description**:

The script will pull the top posts from the subreddit you give it.

It will look throught the posts to find images and then download them to the /data/Images file.

You will need a bot login for reddit. See: https://github.com/reddit-archive/reddit/wiki/OAuth2-Quick-Start-Example#first-steps

This will give you the ID & secret code needed in the /data/config.txt file.  On first run the script will create this file for you to paste them into.


**Usage**

usage: main.py [-h] [-a] sub limit

positional arguments:

  sub          Input subreddit for downloading.
  
  limit        Number of submissions attempted for download.

optional arguments:
  -h, --help   show this help message and exit
  -a, --album  Allow Imgur albums

**Requirements**

Praw

Prawcore


**Notes**

Logging is on at debug as default, it creates a main.log file on run.