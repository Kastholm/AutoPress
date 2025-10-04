import json
import html
import requests as req
import os
import re
import time
from models.chatgpt import ChatGPT
from models.wordpress import WordPress

class AutoPress():

    def __init__(self, name, url, open_ai):
        self.open_ai = open_ai
        self.name = name
        self.url = url
        self.post_fetch_url = f'https://{self.url}/wp-json/wp/v2/posts?per_page=1&page=1'
        self.eligible_posts_arr = []
        self.posts_to_publish = []
        self.webp_image_gen = ''
        self.fetch_compare_articles()
        self.generate_new_articles()
        self.publish_articles()


    def render_html_to_plain_text(self, text):
        pattern = re.compile(r"<[^>]+>")
        clean = pattern.sub("", text)
        return html.unescape(clean)

    def generate_load_files(self):
        if not os.path.exists(self.name):
            os.makedirs(self.name)
        if not os.path.exists(f'{self.name}/articles.json'):
            with open(f'{self.name}/articles.json', 'w') as f:
                json.dump([], f)
        if not os.path.exists(f'{self.name}/gen_articles.json'):
            with open(f'{self.name}/gen_articles.json', 'w') as f:
                json.dump([], f)
        
        with open(f'{self.name}/articles.json', 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        return json_data
        

    def fetch_compare_articles(self):

        fetch_articles_req = req.get(self.post_fetch_url)

        if fetch_articles_req.status_code == 200:
            load_article_json_file = self.generate_load_files()
            fetched_articles_json = fetch_articles_req.json()
            for article in fetched_articles_json:
                article_arr = ({
                    "id": article['id'],
                    "name": html.unescape(article['title']['rendered']),
                    "date": article['date_gmt'],
                    "media": article['featured_media_global']['source_url'],
                    "content": self.render_html_to_plain_text(article['content']['rendered'])
                })

                if article_arr not in load_article_json_file:
                    self.eligible_posts_arr.append(article_arr)
            
            load_article_json_file.extend(self.eligible_posts_arr)

            with open(f'{self.name}/articles.json', 'w', encoding='utf-8') as f:
                json.dump(load_article_json_file, f, indent=4, ensure_ascii=False)
        
        else:
            print('error fetching posts')
            
        return self.eligible_posts_arr

    
    def generate_new_articles(self):
        file_data = self.generate_load_files()
        with open(f'{self.name}/gen_articles.json', 'r', encoding='utf-8') as f:
            gen_articles = json.load(f)

        existing_ids = []
        for article in gen_articles:
            existing_ids.append(article['id'])

        for article in file_data:
            if article['id'] not in existing_ids:
                generated_article = self.open_ai.send_prompt(article)
                parsed_article = json.loads(generated_article)

                #TODO Undersøg om et relevant billede allerede findes i db ud fra titel/desc og brug
                #dette i stedet for at reducerer bruig af tokens.
                generated_image_webp = self.open_ai.generate_img_two(
                    parsed_article['title'], parsed_article['image_url'], 
                    parsed_article['image_prompt']
                    )
                self.webp_image_gen = generated_image_webp
                gen_articles.append(parsed_article)

                self.posts_to_publish.append(parsed_article)
                
                with open(f'{self.name}/gen_articles.json', 'w', encoding='utf-8') as f:
                    json.dump(gen_articles, f, indent=4, ensure_ascii=False)
            else:
                print('Article already generated')


    def publish_articles(self):
        if self.posts_to_publish == []:
            print('No new posts to post')
            return
        
        for post in self.posts_to_publish:
            print('Publish to WP', post)
            WordPress([post], self.webp_image_gen)
                

if __name__ == "__main__":

    open_ai = ChatGPT()
    testSite = AutoPress('nyheder24', 'nyheder24.dk', open_ai)

    #for i in range(100):
    #    testSite = AutoPress('nyheder24', 'nyheder24.dk', open_ai)
    #    time.sleep(600)

    #testSite = AutoPress('dagens', 'dagens.dk', open_ai)


    #TODO hvis billede kommer fra steder uden ophavsret som TikTok/Instagram etc. Så medtag billedet uden AI