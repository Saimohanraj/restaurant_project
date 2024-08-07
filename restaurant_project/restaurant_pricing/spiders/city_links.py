import scrapy


class CitylinksSpider(scrapy.Spider):
    name = "city_links"

    def start_requests(self):
        url = "https://www.chilis.com/locations/us/all"
        yield scrapy.Request(url,callback=self.parse)

    def parse(self, response):
        city_links = response.xpath('//h2/following-sibling::a/@href').getall() 
        for city_link in city_links:
            yield scrapy.Request(response.urljoin(city_link),callback=self.parse_data)

    def parse_data(self, response):
        data = response.xpath('//a[contains(text(),"Order Now")]/@href').getall()  
        for dt in data[1:]:
            with open("restaurant_urls.txt","a") as f:
                f.write(response.urljoin(dt)+"\t"+str(response.url)+"\n")             