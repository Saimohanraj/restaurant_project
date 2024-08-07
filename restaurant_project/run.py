import os

count = 1
with open("restaurant_urls.txt", "r") as f:
    urls = [line.strip() for line in f.readlines()]
for url in urls:
    city_url=url.split("\t")[-1].strip()
    restaurant_url=url.split("\t")[0].strip()
    restaurant_id = restaurant_url.split("=")[-1].strip()

    os.system(f"scrapy crawl chilis -a city_url={city_url} -a restaurant_url={restaurant_url} -o chilis_{str(count)}.json")
    count = count+1