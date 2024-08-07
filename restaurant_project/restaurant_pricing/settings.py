# Scrapy settings for restaurant_pricing project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "restaurant_pricing"

SPIDER_MODULES = ["restaurant_pricing.spiders"]
NEWSPIDER_MODULE = "restaurant_pricing.spiders"


# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 1

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 2
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 16
CONCURRENT_REQUESTS_PER_IP = 1

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'restaurant_pricing.middlewares.RestaurantPricingSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    'restaurant_pricing.middlewares.RestaurantPricingDownloaderMiddleware': 543,
# }
DOWNLOADER_MIDDLEWARES = {
    # "scrapy_html_storage.HtmlStorageMiddleware": 10,
    "rotating_proxies.middlewares.RotatingProxyMiddleware": 610,
    # "rotating_proxies.middlewares.BanDetectionMiddleware": 620,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
    "restaurant_pricing.middlewares.DelayedRetryMiddleware": 543,
}

# DEFAULT_REQUEST_HEADERS = {
#     "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
#     "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
# }

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
# ITEM_PIPELINES = {
#     # "restaurant_pricing.pipelines.RestaurantCustomImagesPipeline": 1,
#     "restaurant_pricing.pipelines.RestaurantImagePipeline": 300,
# }
# DOWNLOADER_MIDDLEWARES = {
#     "scrapy_splash.SplashCookiesMiddleware": 723,
#     "scrapy_splash.SplashMiddleware": 725,
#     "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
# }
# SPLASH_URL = "http://localhost:8050"
# DUPEFILTER_CLASS = "scrapy_splash.SplashAwareDupeFilter"
# HTTPCACHE_STORAGE = "scrapy_splash.SplashAwareFSCacheStorage"
# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = False
# HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = "httpcache"
# TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
# FEED_EXPORT_FIELDS = ["source_id", "name"]
# LOG_LEVEL = ""
# LOG_FILE = "crawler_log.txt"

HTTPCACHE_IGNORE_HTTP_CODES = [403, 504, 503, 404, 400, 401, 500, 502, 408, 406]
RETRY_TIMES = 10
RETRY_HTTP_CODES = [500, 502, 503, 504, 400, 403, 404, 408]
RETRY_HTTP_CODES_WITH_DELAY = [403]
RETRY_DOWNLOAD_DELAY = 10
ROTATING_PROXY_LIST = [""]
