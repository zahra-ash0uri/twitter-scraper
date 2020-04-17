from twitter_scraper import TwitterScraper

"""
    PARAMETERS:
    `` receive_buffer: handler function to manipulate what you want on received tweets
    `` username: a single username string, without '@'
    `` query_search: text string keyword to search in tweets
    `` since, until: datetime range to search within
    `` lang: to specify language
"""


if __name__ == '__main__':
    scraper = TwitterScraper(use_proxy=False)

    def receive_buffer(tweets):
        for t in tweets:
            print(t)
    results = scraper.get_tweets(receive_buffer=receive_buffer, username='shinyza_', query_search='blah-blah',
                                 since='2020-01-01', until='2020-04-01', lang='en')
