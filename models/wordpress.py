import os
import requests
import base64
from slugify import slugify
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

class WordPress:

    def __init__(self, articles, webp_img):
        load_dotenv()
        self.credentials = {
            'user': os.getenv('WP_USERNAME'),
            'pass': os.getenv('WP_APP_PW'),
            'site': os.getenv('WP_PATH')
        }
        self.endpoint = f'https://{self.credentials["site"]}/wp-json/wp/v2/posts'

        if not self.credentials['pass']:
            print('credentials not set')

        self.articles = articles
        self.webp = webp_img

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
                        "slug": slugify(new_article['categories']),
                        "description": new_article['categories_desc'],
                        "parent": 0
                        })
                r = requests.post(
                    fetch_url,
                    json=category,
                    auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                    headers={"Content-Type": "application/json"}
                )
                if r.status_code == 201:
                    category_json = r.json()
                    print(category_json)
                    category_id = category_json['id']
                    print('New Category created')
                else:
                    print('Category request post failed ❌')
            
            return category_id


    def apply_tags(self, new_article):
        if new_article['tags']:
            apply_tag_ids_arr = []
            fetched_fuzzy_tags_arr = []
            fetch_url = f'https://{self.credentials["site"]}/wp-json/wp/v2/tags/?per_page=100&&context=edit'
            tags = [t.strip() for t in new_article['tags'].split(',')]
            
            for tag in tags:
                #See if article tags exist in the database, if so apply tags to array.
                url = f'https://{self.credentials["site"]}/wp-json/wp/v2/tags?slug={slugify(tag)}'
                s = requests.Session()
                s.auth = HTTPBasicAuth(self.credentials['user'], self.credentials['pass'])
                tag_response = requests.get(url, auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']))
                tag_response_json = tag_response.json()

                if tag_response_json == []:
                    tag = ({
                            "name": tag,
                            "slug": slugify(tag),
                            "description": ''
                            })
                    r = requests.post(
                        fetch_url,
                        json=tag,
                        auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                        headers={"Content-Type": "application/json"}
                    )
                    if r.status_code == 201:
                        print('tag data posted')
                        tag_json = r.json()
                        apply_tag_ids_arr.append(tag_json['id'])
                    else:
                        priont('tag data failed request ❌')
                else:
                    apply_tag_ids_arr.append(tag_response_json[0]['id'])

            return apply_tag_ids_arr

    def apply_img(self, new_article):
        
        lib_url = f'https://{self.credentials["site"]}/wp-json/wp/v2/media'

        filename = f"{slugify(new_article['image_title'])}.webp"
        
        r = requests.post(
            lib_url,
            files={'file': (filename, self.webp, 'image/webp')},
            auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
        
        print(f'Image upload status: {r.status_code}')
        print(f'Image upload response: {r.text}')
        
        if r.status_code == 201:
            data = r.json()
            print(data, 'IMAGE DATA REQUESTED')
            
            media_id = data["id"]
            print('ID', media_id)
            
            # Update image metadata
            update_response = requests.post(
                f"{lib_url}/{media_id}",
                json={"alt_text": new_article['image_desc'], "caption": "AI Genereret"},
                auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                headers={"Content-Type": "application/json"}
            )
            print(f'Image metadata update status: {update_response.status_code}')
            
            return media_id
        else:
            print(f'❌ Image upload failed: {r.status_code}, {r.text}')
            return None
            

    def publish_post(self):
        for new_article in self.articles:

            #Connect og vælg cat,tag,jour
            category_id = self.apply_category(new_article)
            print(category_id)
            tag_ids = self.apply_tags(new_article)
            print(tag_ids)
            img_id = self.apply_img(new_article)
            print(img_id)
            
            # Skip posting if image upload failed
            if img_id is None:
                print('❌ Skipping post due to failed image upload')
                continue

            
            #TODO tilvælg en random journalist

            ready_article = ({
                        "title": new_article['title'],
                        "content": new_article['content'],
                        "status": "publish",
                        'featured_media': img_id,
                        'categories': category_id,
                        'tags': tag_ids
            })

            r = requests.post(
                self.endpoint,
                json=ready_article,
                auth=HTTPBasicAuth(self.credentials['user'], self.credentials['pass']),
                headers={"Content-Type": "application/json"}
            )

            print(ready_article,'⚔️')

            if r.status_code == 201:
                print(f'✅ AUTH Connection to new site {self.credentials["site"]} sucess')
            else:
                print(f'⛔ AUTH Connection to new site {self.credentials["site"]} failed: {r.status_code}, {r.text}')
            return
            r.raise_for_status()