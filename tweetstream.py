"""
The TweetStream class is just a simple HTTP client for handling the
twitter firehose.

Usage is pretty simple:

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


The constructor takes two optional arguments, `ioloop` and `clean`.
The `ioloop` argument just lets you specify a specific loop to run on,
and `clean` is just a boolean (False by default) that will strip out
basic data from the twitter message payload.
"""

from tornado.iostream import IOStream, SSLIOStream
from tornado.ioloop import IOLoop
import json
import socket
import time
import base64
import urlparse

TWITTER_APP_USER = "SET_IN_SETTINGS"
TWITTER_APP_PASSWORD = "SET_IN_SETTINGS"
TWITTER_STREAM_HOST = "stream.twitter.com"
TWITTER_STREAM_PORT = 443
TWITTER_STREAM_SCHEME = "https"

class TweetStream(object):
    """ Twitter stream connection """

    def __init__(self, ioloop=None, clean=False):
        """ Just set up the cache list and get first set """
        # prepopulating cache
        self.ioloop = ioloop or IOLoop.instance()
        self.callback = None
        self.error_callback = None
        self._clean_message = clean

    def fetch(self, path, method="GET", callback=None):
        """ Opens the request """
        parts = urlparse.urlparse(path)
        self.method = method
        self.callback = callback
        self.path = parts.path
        self.full_path = self.path
        if parts.query:
            self.full_path += "?%s" % parts.query
        # throwing away empty or extra query arguments
        self.query_args = dict([
            (key, value[0]) for key, value in
            urlparse.parse_qs(parts.query).iteritems()
            if value
        ])
        self.open_twitter_stream()

    def on_error(self, error):
        """ Just a wrapper for the error callback """
        if self.error_callback:
            return self.error_callback(error)
        else:
            raise error

    def open_twitter_stream(self):
        """ Creates the client and watches stream """
        address_info = socket.getaddrinfo(TWITTER_STREAM_HOST,
            TWITTER_STREAM_PORT, socket.AF_INET, socket.SOCK_STREAM,
            0, 0)
        af, socktype, proto = address_info[0][:3]
        socket_address = address_info[0][-1]
        sock = socket.socket(af, socktype, proto)
        stream_class = IOStream
        if TWITTER_STREAM_SCHEME == "https":
            stream_class = SSLIOStream
        self.twitter_stream = stream_class(sock, io_loop=self.ioloop)
        self.twitter_stream.connect(socket_address, self.on_connect)

    def on_connect(self):
        base64string = base64.encodestring("%s:%s" % (TWITTER_APP_USER,
            TWITTER_APP_PASSWORD))[:-1]
        headers = {"Authorization": "Basic %s" % base64string,
                   "Host": "stream.twitter.com"}
        request = ["GET %s HTTP/1.1" % self.full_path]
        for key, value in headers.iteritems():
            request.append("%s: %s" % (key, value))
        request = "\r\n".join(request) + "\r\n\r\n"
        self.twitter_stream.write(str(request))
        self.twitter_stream.read_until("\r\n\r\n", self.on_headers)

    def on_headers(self, response):
        """ Starts monitoring for results. """
        status_line = response.splitlines()[0]
        response_code = status_line.replace("HTTP/1.1", "")
        response_code = int(response_code.split()[0].strip())
        exception = Exception("Could not connect to twitter: %s\n%s" %
            (status_line, response))
        if response_code != 200:
            return self.on_error(exception)
        self.wait_for_message()

    def wait_for_message(self):
        """ Throw a read event on the stack. """
        self.twitter_stream.read_until("\r\n", self.on_result)

    def on_result(self, response):
        """ Gets length of next message and reads it """
        if (response.strip() == ""):
            return self.wait_for_message()
        length = int(response.strip(), 16)
        self.twitter_stream.read_bytes(length, self.parse_json)

    def parse_json(self, response):
        """ Checks JSON message """
        if not response.strip():
            # Empty line, happens sometimes for keep alive
            return self.wait_for_message()
        try:
            response = json.loads(response)
        except ValueError:
            print "Invalid response:"
            print response
            return self.wait_for_message()

        self.parse_response(response)

    def parse_response(self, response):
        """ Parse the twitter message """
        if self._clean_message:
            try:
                text = response["text"]
                name = response["user"]["name"]
                username = response["user"]["screen_name"]
                avatar = response["user"]["profile_image_url_https"]
            except KeyError, exc:
                print "Invalid tweet structure, missing %s" % exc
                return self.wait_for_message()

            response = {
                "type": "tweet",
                "text": text,
                "avatar": avatar,
                "name": name,
                "username": username,
                "time": int(time.time())
            }
        if self.callback:
            self.callback(response)
        self.wait_for_message()
