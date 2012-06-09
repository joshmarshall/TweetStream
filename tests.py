from tornado.testing import AsyncTestCase
import tweetstream
import logging

try:
    import test_settings
except ImportError:
    test_settings = None


class TestTweetStream(AsyncTestCase):

    def setUp(self):
        super(TestTweetStream, self).setUp()
        self.original_app_password = tweetstream.TWITTER_APP_PASSWORD
        tweetstream.TWITTER_APP_PASSWORD = "foobar"

    def tearDown(self):
        super(TestTweetStream, self).tearDown()
        tweetstream.TWITTER_APP_PASSWORD = self.original_app_password

    def test_twitter_stream(self):
        """ Test that the twitter stream is started with module defaults """
        result = {}
        def error_callback(error):
            result["error"] = error
            self.stop()
        stream = tweetstream.TweetStream(ioloop=self.io_loop)
        stream.error_callback = error_callback
        stream.fetch("foobar?whats=up")
        self.wait()
        self.assertTrue("error" in result)

    def test_twitter_stream_with_configuration(self):
        """Test that the twitter stream supports instance configuration."""
        configuration = {
            "twitter_app_username": "newusername",
            "twitter_app_password": "newpassword",
            "twitter_stream_host": "whatever.com",
            "twitter_stream_port": 556,
            "twitter_stream_scheme": "http"
        }
        stream = tweetstream.TweetStream(ioloop=self.io_loop,
            configuration=configuration)
        # this is evil, but until module stuff is removed and
        # proper configuration is refactored it will have to do.
        self.assertEqual("newusername", stream._twitter_app_user)
        self.assertEqual("newpassword", stream._twitter_app_password)
        self.assertEqual("whatever.com", stream._twitter_stream_host)
        self.assertEqual(556, stream._twitter_stream_port)
        self.assertEqual("http", stream._twitter_stream_scheme)


class TestActualTwitterCalls(AsyncTestCase):
    """ Testing actual calls, assuming settings are loaded. """

    def setUp(self):
        super(TestActualTwitterCalls, self).setUp()
        self.original_app_user = tweetstream.TWITTER_APP_USER
        self.original_app_password = tweetstream.TWITTER_APP_PASSWORD
        if test_settings:
            tweetstream.TWITTER_APP_USER = \
                    test_settings.TWITTER_APP_USER
            tweetstream.TWITTER_APP_PASSWORD = \
                    test_settings.TWITTER_APP_PASSWORD

    def tearDown(self):
        super(TestActualTwitterCalls, self).tearDown()
        tweetstream.TWITTER_APP_USER = self.original_app_user
        tweetstream.TWITTER_APP_PASSWORD = self.original_app_password

    def get_message(self, path, clean=False):
        """ Wraps the ioloop start much like self.fetch """
        stream = tweetstream.TweetStream(ioloop=self.io_loop, clean=clean)
        result = {}
        def callback(message):
            """ Save result """
            result["message"] = message
            self.stop()
        stream.fetch(path, callback=callback)
        self.wait()
        # will block until a message comes in or timeout
        return result["message"]

    def test_message(self):
        """ Test that twitter connects. """
        #... if only everyone used 2.7 ...
        if not test_settings:
            logging.debug("Skipping test.")
            return
        result = self.get_message("/1/statuses/sample.json")
        self.assertTrue("user" in result)
        self.assertTrue("text" in result)

    def test_stripped_message(self):
        """ Test that twitter connects and retrieves simple message. """
        if not test_settings:
            logging.debug("Skipping test")
            return
        result = self.get_message("/1/statuses/sample.json", clean=True)
        self.assertTrue("name" in result)
        self.assertTrue("username" in result)
        self.assertTrue("text" in result)
        self.assertTrue(result["type"] == "tweet")

