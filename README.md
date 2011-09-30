The TweetStream class is just a simple HTTP client for handling the
twitter firehose.

Usage is pretty simple:

```python
import tweetstream
tweetstream.TWITTER_APP_USER = "username"
tweetstream.TWITTER_APP_PASSWORD = "password"

def callback(message):
    # this will be called every message
    print message

stream = tweetstream.TweetStream()
stream.fetch("/1/statuses/filter.json?track=foobar", callback=callback)

# if you aren't on a running ioloop...
from tornado.ioloop import IOLoop
IOLoop.instance().start()
```

The constructor takes two optional arguments, `ioloop` and `clean`.
The `ioloop` argument just lets you specify a specific loop to run on,
and `clean` is just a boolean (False by default) that will strip out
basic data from the twitter message payload.

TODO: Implement OAuth header instead of Basic Auth.
