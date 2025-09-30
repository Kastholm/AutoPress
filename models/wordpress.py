import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

class WordPress:

    def __init__(self):
        load_dotenv()
        self.credentials = {
            'user': os.getenv('WP_USERNAME'),
            'pass': os.getenv('WP_APP_PW'),
            'site': os.getenv('WP_PATH')
        }
        self.endpoint = f'https://{self.credentials["site"]}/wp-json/wp/v2/posts'

        if not self.credentials['pass']:
            print('credentials not set')

        #self.articles = articles
        self.articles = [{
                            "title": "Dummy artikel",
                            "content": "<p>Dette er indholdet af en testartikel.</p>",
                            "status": "publish"
                        }]


        #if self.articles == []:
        #    print('No artciles to WordPress')
        #    return

        self.publish_post()

    def connect_to_wordpress(self):
        url = f'{self.credentials["site"]}/wp-json/wp/v2/users/?per_page=100&&context=edit'
        s = requests.Session()
        s.auth = HTTPBasicAuth(self.credentials['user'], self.credentials['pass'])
        response = requests.get(f'https://{url}', auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']))

        if response.status_code == 200:
            print(f'✅ AUTH Connection to new site {self.credentials["site"]} sucess')
        else:
            print(f'⛔ AUTH Connection to new site {self.credentials["site"]} failed: {response.status_code}, {response.text}')
            return

        return response.json()

    def publish_post(self):
        for article in self.articles:

            #Connect og vælg cat,tag,jour

            #Tag og kategori er sat af ChatGPT fra start.
                #De oprettes derefter i WordPress hvis de ikke findes.
                #Hvis eller hvis ikke skal ids returneres, så de kan påsættes artikel til oprettelse
            
            #Journalister - ale journalist ids hentes, og 1 vælges random

            r = requests.post(
                self.endpoint,
                json=article,
                auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                headers={"Content-Type": "application/json"}
            )

            if r.status_code == 201:
                print(f'✅ AUTH Connection to new site {self.credentials["site"]} sucess')
            else:
                print(f'⛔ AUTH Connection to new site {self.credentials["site"]} failed: {r.status_code}, {r.text}')
            return
            r.raise_for_status()

    

if __name__ == "__main__":
    t = WordPress()