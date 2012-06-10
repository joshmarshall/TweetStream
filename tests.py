from tornado.testing import AsyncTestCase
import tweetstream
import logging
import os
import time

TEST_CONSUMER_KEY = os.environ.get("TWEETSTREAM_TEST_CONSUMER_KEY")
TEST_CONSUMER_SECRET = os.environ.get("TWEETSTREAM_TEST_CONSUMER_SECRET")
TEST_ACCESS_TOKEN = os.environ.get("TWEETSTREAM_TEST_ACCESS_TOKEN")
TEST_ACCESS_SECRET = os.environ.get("TWEETSTREAM_TEST_ACCESS_TOKEN_SECRET")

def test_real_config():
    configuration = {
        "twitter_consumer_secret": TEST_CONSUMER_SECRET,
        "twitter_consumer_key": TEST_CONSUMER_KEY,
        "twitter_access_token_secret": TEST_ACCESS_SECRET,
        "twitter_access_token": TEST_ACCESS_TOKEN
    }
    if None in configuration.values():
        logging.debug("Missing one or more test configuration values.")
        return None
    return configuration

class TestTweetStream(AsyncTestCase):

    def test_twitter_stream(self):
        """ Test that the twitter stream is started with module defaults """
        result = {}
        def error_callback(error):
            result["error"] = error
            print error
            self.stop()

        configuration = {
            "twitter_consumer_secret": "ABCDEF1234567890",
            "twitter_consumer_key": "0987654321ABCDEF",
            "twitter_access_token_secret": "1234567890ABCDEF",
            "twitter_access_token": "FEDCBA09123456789",
        }
        stream = tweetstream.TweetStream(configuration, ioloop=self.io_loop)
        stream.set_error_callback(error_callback)
        stream.fetch("/1/statuses/sample.json")
        self.wait()
        self.assertTrue("error" in result)

    def test_twitter_stream_bad_configuration(self):
        """Test the configuration missing values."""
        configuration = {
            "twitter_consumer_secret": "ABCDEF1234567890",
            "twitter_consumer_key": "0987654321ABCDEF",
            "twitter_access_token_secret": "1234567890ABCDEF",
            "twitter_access_token": "FEDCBA09123456789"
        }
        for key in configuration:
            bad_config = configuration.copy()
            del bad_config[key]
            self.assertRaises(tweetstream.MissingConfiguration,
                lambda: tweetstream.TweetStream(bad_config))

    def test_twitter_stream_with_configuration(self):
        """Test that the twitter stream supports instance configuration."""
        configuration = {
            "twitter_consumer_secret": "ABCDEF1234567890",
            "twitter_consumer_key": "0987654321ABCDEF",
            "twitter_access_token_secret": "1234567890ABCDEF",
            "twitter_access_token": "FEDCBA09123456789",
            "twitter_stream_host": "whatever.com",
            "twitter_stream_port": 556,
            "twitter_stream_scheme": "http"
        }
        stream = tweetstream.TweetStream(ioloop=self.io_loop,
            configuration=configuration)
        # this is evil, but until module stuff is removed and
        # proper configuration is refactored it will have to do.
        self.assertEqual(556, stream._twitter_stream_port)
        self.assertEqual("http", stream._twitter_stream_scheme)


class TestActualTwitterCalls(AsyncTestCase):
    """ Testing actual calls, assuming settings are loaded. """

    def get_message(self, path, clean=False):
        """ Wraps the ioloop start much like self.fetch """
        def error_callback(error):
            self.io_loop.stop()
            self.fail(str(error))

        stream = tweetstream.TweetStream(
            configuration=test_real_config(),
            ioloop=self.io_loop, clean=clean)
        stream.set_error_callback(error_callback)
        result = {}
        def callback(message):
            """ Save result """
            if message.get("text"):
                result["message"] = message
                self.stop()
            # otherwise, it's not a tweet we care about...

        stream.fetch(path, callback=callback)
        self.wait()
        # will block until a message comes in or timeout
        # now waiting to keep from hammering the stream connections
        time.sleep(5)
        return result["message"]

    def test_message(self):
        """ Test that twitter connects. """
        #... if only everyone used 2.7 ...
        if not test_real_config():
            logging.debug("Skipping test.")
            return
        result = self.get_message("/1/statuses/sample.json")
        self.assertTrue("user" in result)
        self.assertTrue("text" in result)

    def test_stripped_message(self):
        """ Test that twitter connects and retrieves simple message. """
        if not test_real_config():
            logging.debug("Skipping test")
            return
        result = self.get_message("/1/statuses/sample.json", clean=True)
        self.assertTrue("name" in result)
        self.assertTrue("username" in result)
        self.assertTrue("text" in result)
        self.assertTrue(result["type"] == "tweet")

    def test_search_term(self):
        """Test the statuses with a search term."""
        if not test_real_config():
            logging.debug("Skipping test")
            return
        result = self.get_message("/1/statuses/filter.json?track=twitter")
        self.assertTrue("user" in result)
        self.assertTrue("text" in result)

