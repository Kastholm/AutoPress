import json
import html
import requests as req
import os
import re
from models.chatgpt import ChatGPT
from models.wordpress import WordPress

class AutoPress():

    def __init__(self, name, url, open_ai):
        self.open_ai = open_ai
        self.name = name
        self.url = url
        self.post_fetch_url = f'https://{self.url}/wp-json/wp/v2/posts?per_page=1&page=1'
        self.eligible_posts = []
        self.posts_to_publish = []
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

        r = req.get(self.post_fetch_url)

        if r.status_code == 200:
            file_data = self.generate_load_files()
            fetched_data = r.json()
            for article in fetched_data:
                article_arr = ({
                    "id": article['id'],
                    "name": html.unescape(article['title']['rendered']),
                    "date": article['date_gmt'],
                    "media": article['featured_media_global']['source_url'],
                    "content": self.render_html_to_plain_text(article['content']['rendered'])
                })

                if article_arr not in file_data:
                    self.eligible_posts.append(article_arr)
            
            file_data.extend(self.eligible_posts)
            with open(f'{self.name}/articles.json', 'w', encoding='utf-8') as f:
                json.dump(file_data, f, indent=4, ensure_ascii=False)
        
        else:
            print('error fetching posts')
            
        return self.eligible_posts

    
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

                '''
                Generate an image from the image in generated_article
                and then replace it with the existing image url
                '''

                parsed_article = json.loads(generated_article)
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
            print('Publish', post)
        #Indhent nye genererede artikler og publish dem til WordPress
        #Lav guards for at sikre at det er en korrekt artikel der bliver published
        pass
                

if __name__ == "__main__":

    open_ai = ChatGPT()

    #Thread 1
    testSite = AutoPress('nyheder24', 'nyheder24.dk', open_ai)



    '''
    Burde koden kører i loop hvert 2 min cirka? og hvis den seneste post er en ny for et givent site, så begynd at udgiv den ?
    
    
    1. Fetch artikler og generer filer.
    2. Tjek om om fetched artikel allerede er fetched før via compare med file.
    3. Hvis den er i filen
        - Return
    4. Hvis ikke
        - Returner artiklerne
    '''