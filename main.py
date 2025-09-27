import json
import requests as req
import os

class AutoPress():

    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.post_fetch_url = f'https://{self.url}/wp-json/wp/v2/posts?per_page=10&page=1'
        self.eligible_posts = []
        

    def generate_load_files(self):
        if not os.path.exists(self.name):
            os.makedirs(self.name)
        if not os.path.exists(f'{self.name}/articles.json'):
            with open(f'{self.name}/articles.json', 'w') as f:
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
                    "name": article['title']['rendered'],
                    "date": article['date_gmt']
                })

                if article_arr not in file_data:
                    self.eligible_posts.append(article_arr)
            
            file_data.extend(self.eligible_posts)
            with open(f'{self.name}/articles.json', 'w', encoding='utf-8') as f:
                json.dump(file_data, f, indent=4, ensure_ascii=False)
        
        else:
            print('error fetching posts')
            
        return self.eligible_posts

    
    def generate_articles(self):
        #connect to OpenAI
        pass

    def publish_articles(self):
        pass
                

if __name__ == "__main__":

    testSite = AutoPress('nyheder24', 'nyheder24.dk')

    test = testSite.fetch_compare_articles()

    print(test)


    '''
    Burde koden kører i loop hvert 2 min cirka? og hvis den seneste post er en ny for et givent site, så begynd at udgiv den ?
    
    
    1. Fetch artikler og generer filer.
    2. Tjek om om fetched artikel allerede er fetched før via compare med file.
    3. Hvis den er i filen
        - Return
    4. Hvis ikke
        - Returner artiklerne
    
    
    '''