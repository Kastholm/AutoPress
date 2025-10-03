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

        self.articles = [{
                            "title": "Dummy artikel",
                            "content": "<p>Dette er indholdet af en testartikel.</p>",
                            "status": "publish",
                            'image_url': 'https://media.mgdk.dk/wp-content/uploads/sites/2/2025/08/Shutterstock_2054600435.jpg',
                            'categories': 'Test',
                            'categories_desc': 'Test',
                            'tags': 'test, testt, testtt'
                        }]

        if self.articles == []:
            print('No articles to WordPress')
            return

        self.publish_post()


    def connect_to_wordpress(self, path):
        url = f'https://{self.credentials["site"]}/wp-json/wp/v2/{path}/?per_page=100&&context=edit'
        s = requests.Session()
        s.auth = HTTPBasicAuth(self.credentials['user'], self.credentials['pass'])
        response = requests.get(url, auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']))

        if response.status_code == 200:
            print(f'✅ AUTH Connection to new site {self.credentials["site"]}/{path} sucess')
        else:
            print(f'⛔ AUTH Connection to new site {self.credentials["site"]}/{path} failed: {response.status_code}, {response.text}')
            return

        return url, response.json()


    def apply_category(self, new_article):
        if new_article['categories']:
            category_id = ''
            fetch_url, fetched_categories = self.connect_to_wordpress('categories')
            
            for fetched_category in fetched_categories:
                if fetched_category['name'] == new_article['categories']:
                    print('Category in use')
                    category_id = fetched_category['id']
                    break
            #If category_id is empy it indicates that no categories was found in the db
            if category_id == '':
                category = ({
                        "name": new_article['categories'],
                        "slug": new_article['categories'].lower(),
                        "description": new_article['categories_desc'],
                        "parent": 0
                        })
                r = requests.post(
                    fetch_url,
                    json=category,
                    auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                    headers={"Content-Type": "application/json"}
                )
                category_json = r.json()
                print(category_json)
                category_id = category_json['id']
                print('Doesnt exist, create new cat')
            
            return category_id


    def apply_tags(self, new_article):
        if new_article['tags']:
            tag_ids = []
            fetch_url, _ = self.connect_to_wordpress('tags')
            tags = [t.strip() for t in new_article['tags'].split(',')]
            
            for tag in tags:
                url = f'https://{self.credentials["site"]}/wp-json/wp/v2/tags?search={tag}'
                s = requests.Session()
                s.auth = HTTPBasicAuth(self.credentials['user'], self.credentials['pass'])
                response = requests.get(url, auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']))
                fetched_fuzzy_tags = response.json()

                for fuzzy_tag in fetched_fuzzy_tags:
                    
                    if fuzzy_tag['name'] == tag:
                        print(tag, fuzzy_tag['name'])
                        tag_ids.append(fuzzy_tag['id'])

                    


                
                #if tag not in fuzzy_tag['name']:
                #    print('not exist tag')
                #    tag = ({
                #            "name": tag,
                #            "slug": tag.lower(),
                #            "description": ''
                #            })
                #    r = requests.post(
                #        fetch_url,
                #        json=tag,
                #        auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                #        headers={"Content-Type": "application/json"}
                #    )
                #    tag_json = r.json()
                #    tag_ids.append(tag_json['id'])

            return tag_ids
            



            # EVT GET /wp/v2/tags?search=navn TODO

    def publish_post(self):
        for new_article in self.articles:

            #Connect og vælg cat,tag,jour
            category_id = self.apply_category(new_article)
            print(category_id)
            tag_ids = self.apply_tags(new_article)
            print(tag_ids)

            #TAGS
            



            #Journalister - ale journalist ids hentes, og 1 vælges random

            ready_article = ({
                        "title": "Dummy artikel",
                        "content": "<p>Dette er indholdet af en testartikel.</p>",
                        "status": "publish",
                        'image_url': 'https://media.mgdk.dk/wp-content/uploads/sites/2/2025/08/Shutterstock_2054600435.jpg',
                        'categories': category_id,
                        'tags': tag_ids
            })

            r = requests.post(
                self.endpoint,
                json=ready_article,
                auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                headers={"Content-Type": "application/json"}
            )

            print(new_article,'⚔️')

            if r.status_code == 201:
                print(f'✅ AUTH Connection to new site {self.credentials["site"]} sucess')
            else:
                print(f'⛔ AUTH Connection to new site {self.credentials["site"]} failed: {r.status_code}, {r.text}')
            return
            r.raise_for_status()


if __name__ == "__main__":
    t = WordPress()