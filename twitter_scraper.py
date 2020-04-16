import json, re, datetime, random, http.cookiejar
import urllib.request, urllib.parse, urllib.error
from pyquery import PyQuery


class TwitterScraper:
    def __init__(self, use_proxy=True):
        self.use_proxy = use_proxy
        self.tweetCriteria = dict()

    user_agents = [
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:63.0) Gecko/20100101 Firefox/63.0',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:62.0) Gecko/20100101 Firefox/62.0',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:61.0) Gecko/20100101 Firefox/61.0',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:63.0) Gecko/20100101 Firefox/63.0',
        'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0 Safari/605.1.15',
    ]

    @staticmethod
    def _get_proxy(use_proxy):
        if not use_proxy:
            return None
        config = {
            "ip": '',
            "port": ''
        }
        return '{}:{}'.format(config.get('ip'), config.get('port'))

    def get_tweets(self,
                   receive_buffer=None,
                   buffer_length=5,
                   username: str = None,
                   query_search: str = None,
                   since: str = None,
                   until: str = None,
                   lang='fa'
                   ):
        self.tweetCriteria['lang'] = lang
        if username:
            self.tweetCriteria['username'] = username
        if query_search:
            self.tweetCriteria['query_search'] = query_search
        if since:
            self.tweetCriteria['since'] = since
        if until:
            self.tweetCriteria['until'] = until

        cookie_jar = http.cookiejar.CookieJar()
        user_agent = random.choice(TwitterScraper.user_agents)
        proxy = self._get_proxy(use_proxy=self.use_proxy)
        refresh_cursor = ''
        has_more = True
        results = []
        results_aux = []
        while has_more:
            json = TwitterScraper.get_json_response(criteria=self.tweetCriteria,
                                                    refresh_cursor=refresh_cursor,
                                                    cookie_jar=cookie_jar,
                                                    proxy=proxy,
                                                    user_agent=user_agent)
            if len(json['items_html'].strip()) == 0:
                break
            refresh_cursor = json['min_position']
            has_more = json['has_more_items']
            scraped_tweets = PyQuery(json['items_html'])
            # Remove incomplete tweets withheld by Twitter Guidelines
            scraped_tweets.remove('div.withheld-tweet')
            tweets = scraped_tweets('div.js-stream-tweet')
            if len(tweets) == 0:
                break
            for tweet_html in tweets:
                tweetpq = PyQuery(tweet_html)
                tweet = dict()

                date_sec = int(tweetpq("small.time span.js-short-timestamp").attr("data-time"))
                tweet["created_at"] = datetime.datetime.fromtimestamp(date_sec, tz=datetime.timezone.utc) \
                    .strftime("%a %b %d %X +0000 %Y")
                tweet["id"] = int(tweetpq.attr("data-tweet-id"))

                in_reply_to_section = tweetpq("div.ReplyingToContextBelowAuthor")
                tweet["in_reply_to_status_id"] = int(tweetpq.attr("data-conversation-id")) if \
                    tweetpq.attr("data-conversation-id") != str(tweet["id"]) else None
                tweet["in_reply_to_screen_name"] = None
                tweet['in_reply_to_user_id'] = None
                for item in in_reply_to_section.items("a"):
                    screen_name = item.attr("href").replace('/', '')
                    user_id = int(item.attr("data-user-id"))
                    tweet["in_reply_to_screen_name"] = screen_name
                    tweet['in_reply_to_user_id'] = user_id
                    break
                quoted_tweet = tweetpq("div.content")
                quoted_tweet = quoted_tweet("div.QuoteTweet")
                if quoted_tweet:
                    quoted_status = dict()
                    quoted_status["user"] = dict()
                    quoted_tweet = quoted_tweet("div.QuoteTweet-container")
                    quoted_tweet = quoted_tweet("div.QuoteTweet-innerContainer")
                    quoted_status["id"] = quoted_tweet.attr("data-item-id")
                    quoted_status["created_at"] = None
                    quoted_status["user"]["screen_name"] = quoted_tweet.attr("data-screen-name")
                    quoted_status["user"]["id"] = quoted_tweet.attr("data-user-id")
                    quoted_tweet = quoted_tweet("div.tweet-content")
                    quoted_tweet = quoted_tweet("div.QuoteTweet-text")
                    quoted_status["lang"] = quoted_tweet.attr("lang")
                    quoted_status["text"] = quoted_tweet.text()
                    tweet["quoted_status"] = quoted_status

                tweet["user"] = dict()
                tweet["user"]["name"] = tweetpq.attr("data-name")
                tweet["user"]["screen_name"] = tweetpq.attr("data-screen-name")
                tweet["user"]["id"] = int(tweetpq.attr("data-user-id"))

                if not tweet["in_reply_to_screen_name"] and tweet["in_reply_to_status_id"]:
                    tweet["in_reply_to_screen_name"] = tweet["user"]["screen_name"]
                    tweet['in_reply_to_user_id'] = tweet["user"]["id"]

                tweet["retweet_count"] = int(tweetpq("span.ProfileTweet-action--retweet span.ProfileTweet-actionCount").
                                             attr("data-tweet-stat-count").replace(",", ""))
                tweet["favorite_count"] = int(
                    tweetpq("span.ProfileTweet-action--favorite span.ProfileTweet-actionCount").attr(
                        "data-tweet-stat-count").replace(",", ""))
                tweet["reply_count"] = int(tweetpq("span.ProfileTweet-action--reply span.ProfileTweet-actionCount").
                                           attr("data-tweet-stat-count").replace(",", ""))

                tweet["url"] = 'https://twitter.com' + tweetpq.attr("data-permalink-path")
                tweet["lang"] = lang

                urls = []
                for link in tweetpq("a"):
                    try:
                        urls.append({
                            "expanded_url": link.attrib["data-expanded-url"]
                        })
                    except KeyError:
                        pass

                _user_mentions = tweetpq("div.js-tweet-text-container")
                user_mentions = list()
                for mention in _user_mentions.items("a"):
                    if mention and mention.attr("data-mentioned-user-id"):
                        user_mentions.append({
                            "id": int(mention.attr("data-mentioned-user-id")),
                            "screen_name": mention.attr("href").replace('/', '')
                        })


                content = tweetpq("p.js-tweet-text")
                tweet["text"] = content.text()

                if 'Emoji--forText' in str(tweetpq("p.TweetTextSize")):
                    emojies = ''
                    for img in tweetpq("p.TweetTextSize").items('img'):
                        emj = img("img.Emoji--forText").attr("alt")
                        emojies = emojies + emj
                    tweet["text"] = tweet["text"] + ' ' + emojies

                # for attached medias
                if content("a.twitter-timeline-link"):
                    attached_media_url = content("a.twitter-timeline-link").attr("href")
                    tweet["text"] = re.sub(r"pic.twitter.com\S+", " " + attached_media_url, tweet["text"])

                hashtags = " ".join(re.compile('(#\\w*)').findall(tweet["text"]))
                tweet["entities"] = dict()
                tweet["entities"]["urls"] = urls
                media_container = tweetpq("div.AdaptiveMediaOuterContainer")
                if media_container:
                    media = []
                    media_element = dict()
                    media_element["id"] = None
                    media_element["expanded_url"] = tweet["url"] + "/photo/1"
                    if 'PlayableMedia--gif' in str(media_container):
                        media_element["type"] = 'animated_gif'
                        url = re.compile("(https\S+)").findall(media_container("div.PlayableMedia-player").attr("style"))
                        media_element["media_url"] = url[0].replace('\')', '')
                    if 'PlayableMedia--video' in str(media_container):
                        media_element["type"] = 'video'
                        media_element["expanded_url"] = tweet["url"] + "/video/1"
                    if 'AdaptiveMedia-singlePhoto' in str(media_container):
                        media_element["type"] = 'photo'

                    media.append(media_element)
                    tweet["entities"]["media"] = media

                tweet["entities"]["user_mentions"] = user_mentions
                tweet["entities"]["hashtags"] = [hashtag for hashtag in hashtags.split()]
                tweet["entities"]["symbols"] = []
                geo_span = tweetpq('span.Tweet-geo')
                if len(geo_span) > 0:
                    tweet["geo"] = geo_span.attr('title')
                else:
                    tweet["geo"] = ''


                results.append(tweet)
                results_aux.append(tweet)
                if receive_buffer and len(results_aux) >= buffer_length:
                    receive_buffer(results_aux)
                    results_aux = []

        print("{} tweets gathered up to now!".format(len(results)))
        receive_buffer(results_aux)
        return results

    @staticmethod
    def get_json_response(criteria, refresh_cursor, cookie_jar, proxy=None, user_agent=None, debug=False):
        """Invoke an HTTP query to Twitter.
        Should not be used as an API function. A static method.
        """
        url = "https://twitter.com/i/search/timeline?"

        if not criteria.get('topTweets', False):
            url += "f=tweets&"

        url += ("vertical=news&q=%s&src=typd&%s"
                "&include_available_features=1&include_entities=1&max_position=%s"
                "&reset_error_state=false")

        urlGetData = ''

        if criteria.get('query_search', None):
            urlGetData += criteria.get('query_search')

        if criteria.get('username', None):
            username = [' from:' + criteria['username']]
            urlGetData += ' OR'.join(username)

        if criteria.get('since', None):
            urlGetData += ' since:' + criteria.get('since')

        if criteria.get('until', None):
            urlGetData += ' until:' + criteria.get('until')

        if criteria.get('lang', None):
            urlLang = 'l=' + criteria.get('lang') + '&'
        else:
            urlLang = ''
        url = url % (urllib.parse.quote(urlGetData.strip()), urlLang, urllib.parse.quote(refresh_cursor))
        print(url)
        user_agent = user_agent or TwitterScraper.user_agents[0]
        headers = [
            ('Host', "twitter.com"),
            ('User-Agent', user_agent),
            ('Accept', "application/json, text/javascript, */*; q=0.01"),
            ('Accept-Language', "en-US,en;q=0.5"),
            ('X-Requested-With', "XMLHttpRequest"),
            ('Referer', url),
            ('Connection', "keep-alive")
        ]

        if proxy:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http://': proxy, 'https://': proxy}),
                                                 urllib.request.HTTPCookieProcessor(cookie_jar))
        else:
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        opener.addheaders = headers

        if debug:
            print(url)
            print('\n'.join(h[0] + ': ' + h[1] for h in headers))

        try:
            response = opener.open(url)
            jsonResponse = response.read()
        except Exception as e:
            print("An error occured during an HTTP request:", str(e))
            # print("Try to open in browser: https://twitter.com/search?q=%s&src=typd" % urllib.parse.quote(urlGetData))
            raise (e)

        try:
            s_json = jsonResponse.decode()
            dataJson = json.loads(s_json)
        except Exception as e:
            print("Invalid response from Twitter or Parsing Error!")
            raise (e)

        if debug:
            print(s_json)
            print("---\n")

        return dataJson


if __name__ == '__main__':
    scraper = TwitterScraper(use_proxy=False)

    """
        receive_buffer: function called in TwitterScraper.get_tweets to manipulate whatever you want on received tweets.
    """

    def receive_buffer(tweets):
        for t in tweets:
            print(t)
    results = scraper.get_tweets(receive_buffer=receive_buffer, username='shinyza_', query_search='blah-blah',
                                 since='2020-01-01', until='2020-04-01', lang='en')
